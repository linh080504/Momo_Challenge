import hmac
import json
import secrets
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..analyzer.contract import SCHEMA, AnalyzerError
from ..analyzer.providers.llm import PROMPT_VERSION, QWEN_MODEL
from ..analyzer.providers.ocr import image_for
from ..analyzer.signals.knowledge import VERSION as KNOWLEDGE_VERSION
from ..db.store import Login
from ..evidence.url_gateway import inspect_url
from ..ops.alerts import alert_preview
from ..ops.brief import brief
from ..ops.investigation import run_workspace
from ..qr.checks import evaluate, rebuild
from ..reports.proof import issue_result
from ..schemas.requests import AnalyzeIn, DecisionIn, LoginIn, ProofIn, QrIn, QrResult, ReportIn, ReviewIn, SampleReviewIn, SplitReportIn
from ..sharing.summaries import summary_for

MAX_BODY_BYTES = 7_100_000


def body_contract(schema):
    return {"requestBody": {"required": True, "content": {"application/json": {"schema": schema.model_json_schema()}}}}


async def body_as(request, schema):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "Dữ liệu vượt quá giới hạn. Mỗi ảnh tối đa 5 MB.")
        body.extend(chunk)
    try:
        return schema.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, "Dữ liệu gửi lên không đúng định dạng.") from exc


def make_routes(settings, store, signer, limits, users, analyzer):
    router = APIRouter()

    def limit(request, action, count, account=None):
        ip = request.client.host if request.client else "unknown"
        key = (action, "account", account) if account else (action, "ip", ip)
        if not limits.take(key, count):
            raise HTTPException(429, "Bạn đã gửi nhiều yêu cầu. Hãy thử lại sau một phút.")

    def optional_identity(authorization: Annotated[str | None, Header()] = None):
        if authorization is None:
            return None
        if not authorization.startswith("Bearer ") or len(authorization) > 100:
            raise HTTPException(401, "Vui lòng đăng nhập.")
        digest = signer.digest("session", authorization[7:])
        with Session(store.engine) as session:
            admin = session.get(Login, digest)
            if admin is None or admin.expires <= int(time.time()):
                raise HTTPException(401, "Phiên đăng nhập đã hết hạn.")
            if users.get(admin.email, (None, None))[1] != admin.role:
                raise HTTPException(401, "Tài khoản không còn hoạt động.")
            return admin.email, admin.role, digest

    def identity(user=Depends(optional_identity)):
        if user is None:
            raise HTTPException(401, "Vui lòng đăng nhập.")
        return user

    def operator(user=Depends(identity)):
        if user[1] != "ops":
            raise HTTPException(403, "Chỉ tài khoản vận hành được dùng chức năng này.")
        return user

    def proof(token, user):
        claim = signer.read("analysis", token)
        if claim is None:
            raise HTTPException(422, "Kết quả phân tích đã hết hạn. Hãy kiểm tra lại.")
        if claim["owner"] and (not user or signer.digest("reporter", user[0]) != claim["owner"]):
            raise HTTPException(403, "Kết quả thuộc một phiên đăng nhập khác.")
        return claim

    @router.get("/health")
    def health():
        return {"status": "ok", "version": settings.app_version}

    @router.get("/ready")
    def ready():
        store.ready()
        return {"status": "ready", "version": settings.app_version}

    @router.post("/v1/auth/login")
    def login(data: LoginIn, request: Request):
        limit(request, "login", 10)
        email = data.email.strip().lower()
        password, role = users.get(email, ("", None))
        valid = hmac.compare_digest(signer.digest("password", password), signer.digest("password", data.password))
        if not (valid and role):
            raise HTTPException(401, "Email hoặc mật khẩu chưa đúng.")
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with store.write() as session:
            session.execute(delete(Login).where(Login.expires <= now))
            session.add(Login(digest=signer.digest("session", token), email=email, role=role, expires=now + 14400))
        return {"token": token, "email": email, "role": role}

    @router.get("/v1/auth/me")
    def me(user=Depends(identity)):
        return {"email": user[0], "role": user[1]}

    @router.delete("/v1/auth/session")
    def logout(user=Depends(identity)):
        with store.write() as session:
            session.execute(delete(Login).where(Login.digest == user[2]))
        return {"signed_out": True}

    @router.delete("/v1/me/reports")
    def delete_reports(user=Depends(identity)):
        return {"deleted": store.delete_reports(signer.digest("reporter", user[0]))}

    async def analysis_events(request, user):
        if user:
            limit(request, "demo-analyze-ip", settings.demo_analysis_per_minute)
            limit(request, "analyze", settings.demo_analysis_per_minute, user[0])
        else:
            limit(request, "analyze", settings.analysis_per_minute)
        data = await body_as(request, AnalyzeIn)
        if data.website_html is not None and (not data.website_html.strip() or not data.url):
            raise HTTPException(422, "Hãy nhập địa chỉ website và đoạn HTML cần kiểm tra.")
        if data.qr_payload is not None:
            data.qr_payload = data.qr_payload.strip()
        for value in (data.url, data.qr_payload if (data.qr_payload or "").lower().startswith(("http://", "https://")) else None):
            if value is not None:
                try:
                    inspect_url(value)
                except (ValueError, UnicodeError) as exc:
                    raise HTTPException(422, "Địa chỉ web không hợp lệ.") from exc
        if data.image_kind == "receipt" and data.image_base64 is None:
            raise HTTPException(422, "Hãy chọn ảnh biên lai.")
        if data.audio_base64 is not None and data.image_base64 is not None:
            raise HTTPException(422, "Mỗi lượt kiểm tra hỗ trợ một tệp đính kèm.")
        if data.audio_base64 is None and data.qr_payload is None and not (data.text.strip() or data.url or data.image_base64):
            raise HTTPException(422, "Hãy dán nội dung, nhập link, QR hoặc tải tệp.")
        if data.audio_base64 == "" or (data.qr_payload is not None and not data.qr_payload.strip()):
            raise HTTPException(422, "Dữ liệu tệp hoặc mã QR trống.")
        image = await run_in_threadpool(image_for, data)
        events = analyzer.events(data, image)
        first = await run_in_threadpool(next, events)
        return first, events

    def result_for(event, user):
        return issue_result(event, signer, signer.digest("reporter", user[0]) if user else None)

    @router.post("/v1/analyze", openapi_extra=body_contract(AnalyzeIn), responses={
        200: {"content": {"application/json": {"schema": SCHEMA}}}
    })
    async def analyze_once(request: Request, user=Depends(optional_identity)):
        _, events = await analysis_events(request, user)
        return await run_in_threadpool(lambda: result_for(next(item for item in events if "result" in item), user))

    @router.post("/v1/analyze/stream", openapi_extra=body_contract(AnalyzeIn), response_class=StreamingResponse,
                 responses={200: {"description": "Tiến trình và một kết quả hoặc lỗi cuối, một JSON mỗi dòng.",
                                  "content": {"application/x-ndjson": {"schema": {"type": "string"}}}}})
    async def stream_analysis(request: Request, user=Depends(optional_identity)):
        first, events = await analysis_events(request, user)

        def stream():
            yield json.dumps(first, ensure_ascii=False) + "\n"
            try:
                for item in events:
                    if "result" in item:
                        item = {"result": result_for(item, user)}
                    yield json.dumps(item, ensure_ascii=False) + "\n"
            except AnalyzerError as exc:
                yield json.dumps({"error": exc.message, "status": exc.status}, ensure_ascii=False) + "\n"
            except (OSError, SQLAlchemyError):
                yield json.dumps({"error": "Không thể hoàn tất phân tích. Hãy thử lại.", "status": 503}, ensure_ascii=False) + "\n"

        return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"X-Accel-Buffering": "no"})

    @router.post("/v1/reports", status_code=201)
    def report(data: ReportIn, request: Request, user=Depends(identity)):
        limit(request, "report", settings.reports_per_minute, user[0])
        claim = proof(data.analysis_id, user)
        campaign_id = store.report(claim, signer.digest("reporter", user[0]))
        if campaign_id is None:
            raise HTTPException(409, "Kết quả này đã được báo cáo.")
        return {"campaign_id": campaign_id}

    def titled(campaign):
        return {**campaign, **brief(campaign)}

    @router.get("/v1/ops/campaigns")
    def campaigns(state: Literal["pending", "approved", "rejected"] | None = None, _user=Depends(operator)):
        return [titled(campaign) for campaign in store.campaigns(state)]

    @router.get("/v1/ops/overview")
    def overview(_user=Depends(operator)):
        return store.overview()

    @router.get("/v1/ops/system")
    def system_status(_user=Depends(operator)):
        return {
            "app_version": settings.app_version,
            "prompt_version": PROMPT_VERSION,
            "knowledge_version": KNOWLEDGE_VERSION,
            "qwen_model": QWEN_MODEL if settings.dashscope_api_key.get_secret_value().strip() else None,
            "safe_browsing_configured": bool(settings.safe_browsing_key),
            "speech_configured": bool(settings.whisper_command and settings.whisper_model_path),
            "website_capture_enabled": settings.website_capture_enabled,
            "fraud_url_model": analyzer.fraud_url.version if analyzer.fraud_url else None,
        }

    @router.get("/v1/ops/campaigns/{campaign_id}")
    def campaign(campaign_id: str, _user=Depends(operator)):
        found = store.campaign_investigation(campaign_id)
        if found is None:
            raise HTTPException(404, "Không tìm thấy chiến dịch.")
        return {**titled(found[0]), "workspace": run_workspace(*found, settings, limits),
                "alerts": alert_preview(found[0])}

    @router.get("/v1/ops/campaigns/{campaign_id}/samples")
    def campaign_samples(campaign_id: str, after: Annotated[str, Query(max_length=64)] = "",
                         _user=Depends(operator)):
        samples = store.campaign_samples(campaign_id, after)
        if samples is None:
            raise HTTPException(404, "Không tìm thấy chiến dịch.")
        return samples

    @router.post("/v1/ops/campaigns/{campaign_id}/samples/{report_id}/review")
    def label_sample(campaign_id: str, report_id: str, data: SampleReviewIn, user=Depends(operator)):
        review = store.label_sample(campaign_id, report_id, user[0], data.label, data.revision)
        if review is None:
            raise HTTPException(409, "Mẫu đã thay đổi hoặc không còn trong hồ sơ. Hãy tải lại.")
        return review

    @router.post("/v1/ops/campaigns/{campaign_id}/samples/{report_id}/split")
    def split_sample(campaign_id: str, report_id: str, data: SplitReportIn, user=Depends(operator)):
        report = store.split_sample(campaign_id, report_id, user[0], data.revision)
        if report is None:
            raise HTTPException(409, "Chỉ tách được báo cáo từ hồ sơ chờ duyệt còn ít nhất một báo cáo khác. Hãy tải lại hồ sơ.")
        return report

    @router.get("/v1/ops/feedback")
    def verified_feedback(_user=Depends(operator)):
        return {"schema_version": 1, "samples": store.verified_feedback()}

    @router.get("/v1/ops/feedback/samples")
    def reviewed_samples(after: Annotated[str, Query(max_length=64)] = "", _user=Depends(operator)):
        return store.reviewed_sample_export(after)

    @router.post("/v1/ops/campaigns/{campaign_id}/decision")
    def decide(campaign_id: str, data: DecisionIn, user=Depends(operator)):
        updated = store.review(campaign_id, user[0], data.decision, data.revision)
        if updated is None:
            raise HTTPException(409, "Chiến dịch đã thay đổi. Hãy tải lại trước khi quyết định.")
        return {**titled(updated), "alerts": alert_preview(updated)}

    @router.post("/v1/ops/campaigns/{campaign_id}/review")
    def edit_review(campaign_id: str, data: ReviewIn, user=Depends(operator)):
        updated = store.review(campaign_id, user[0], "edit_group", data.revision, data.group)
        if updated is None:
            raise HTTPException(409, "Chiến dịch đã thay đổi. Hãy tải lại trước khi phân loại.")
        return titled(updated)

    @router.post("/v1/shares", status_code=201)
    def create_share(data: ProofIn, request: Request, user=Depends(optional_identity)):
        limit(request, "share", 10)
        claim = proof(data.analysis_id, user)
        return {"token": signer.issue("share", {"risk": claim["risk"]}, 86400)}

    @router.get("/v1/shares/{token}")
    def read_share(token: str):
        claim = signer.read("share", token) if len(token) <= 512 else None
        if claim is None:
            raise HTTPException(404, "Liên kết không hợp lệ hoặc đã hết hạn.")
        return summary_for(claim["risk"])

    @router.post("/v1/qr/parse", openapi_extra=body_contract(QrIn), response_model=QrResult)
    async def parse_qr(request: Request):
        limit(request, "qr", 10)
        data = await body_as(request, QrIn)
        _, result = await run_in_threadpool(evaluate, data, store, signer, settings, analyzer.safe_browsing)
        return result

    @router.post("/v1/qr/build", openapi_extra=body_contract(QrIn))
    async def build_qr(request: Request):
        limit(request, "qr", 10)
        data = await body_as(request, QrIn)
        qr, result = await run_in_threadpool(evaluate, data, store, signer, settings)
        if qr is None or not data.confirmed or result["risk"] != "low":
            raise HTTPException(409, "Cần mã QR nguy cơ thấp và xác nhận người nhận trước khi tạo lại.")
        return {"payload": rebuild(qr)}

    return router

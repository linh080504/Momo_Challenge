"""Create the ignored local environment with separate demo accounts."""

from pathlib import Path
from secrets import token_urlsafe

root = Path(__file__).resolve().parents[1]
example = (root / ".env.example").read_text(encoding="utf-8")
credentials = {
    "APP_SECRET": token_urlsafe(48),
    "DEMO_USER_EMAIL": "demo.user@example.test",
    "DEMO_USER_PASSWORD": token_urlsafe(16),
    "DEMO_OPS_EMAIL": "demo.ops@example.test",
    "DEMO_OPS_PASSWORD": token_urlsafe(16),
}

try:
    with (root / ".env").open("x", encoding="utf-8") as destination:
        for line in example.splitlines():
            name = line.partition("=")[0]
            destination.write(f"{name}={credentials[name]}\n" if name in credentials else line + "\n")
except FileExistsError:
    print(".env already exists. Keep the current settings.")
else:
    print("Local .env created. Open it to read the two local demo accounts.")

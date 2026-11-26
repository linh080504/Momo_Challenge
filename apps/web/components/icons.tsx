// Icon SVG nội tuyến (nét 2px, kiểu outline). Icon chỉ là phụ; ý nghĩa luôn có chữ đi kèm.

type IconProps = { className?: string };

function Icon({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  );
}

export const ShieldIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <path d="M12 3 4 6v5.5c0 4.7 3.2 8.4 8 9.5 4.8-1.1 8-4.8 8-9.5V6l-8-3Z" />
    <path d="m9 12 2.2 2.2L15.5 10" />
  </Icon>
);

export const WarningIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9.5v4" />
    <path d="M12 17h.01" />
  </Icon>
);

export const InfoIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5" />
    <path d="M12 8h.01" />
  </Icon>
);

export const QuestionIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5a2.5 2.5 0 1 1 3.6 2.2c-.7.4-1.1.9-1.1 1.8" />
    <path d="M12 17h.01" />
  </Icon>
);

export const CheckIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </Icon>
);

export const PhotoIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <circle cx="9" cy="10" r="1.5" />
    <path d="m21 16-5-5-8 8" />
  </Icon>
);

export const DocumentIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" />
    <path d="M14 3v5h5" />
    <path d="M9 13h6M9 17h4" />
  </Icon>
);

export const CloseIcon = ({ className }: IconProps) => (
  <Icon className={className}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Icon>
);

export const SpinnerIcon = ({ className }: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
    className={`spin motion-safe:animate-spin ${className ?? ""}`}
  >
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={3} opacity={0.25} />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth={3} strokeLinecap="round" />
  </svg>
);

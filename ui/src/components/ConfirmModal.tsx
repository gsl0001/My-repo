import { useEffect, type ReactNode } from "react";

// Small confirm dialog used for destructive / order-placing actions.
// Dismiss via Cancel, backdrop click, or Esc.
export function ConfirmModal({
  title, body, confirmLabel = "Confirm", danger = false, onConfirm, onCancel,
}: {
  title: string;
  body: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter") onConfirm();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel, onConfirm]);

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={onCancel}>
      <div
        className={`bg-panel border ${danger ? "border-down" : "border-accent"} rounded-lg p-5 w-[360px]`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-strong font-bold mb-1">{title}</div>
        <div className="text-muted text-[12px] mb-4">{body}</div>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-[5px] rounded-md border border-edge text-body hover:bg-[#0c1320]">
            Cancel
          </button>
          <button
            autoFocus
            onClick={onConfirm}
            className={`px-3 py-[5px] rounded-md font-bold ${danger ? "bg-down text-white" : "bg-accent text-black"}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

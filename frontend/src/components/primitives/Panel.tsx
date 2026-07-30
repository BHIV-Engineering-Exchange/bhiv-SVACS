import clsx from "clsx";
import { ReactNode } from "react";

interface PanelProps {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  noPad?: boolean;
  overflowVisible?: boolean;
}

export default function Panel({
  title,
  right,
  children,
  className,
  bodyClassName,
  noPad,
  overflowVisible,
}: PanelProps) {
  return (
    <section className={clsx("panel flex h-full min-h-0 flex-col", !overflowVisible && "overflow-hidden", className)}>
      {title && (
        <header className="panel-header">
          <h3 className="panel-title">{title}</h3>
          {right && <div className="flex items-center gap-2">{right}</div>}
        </header>
      )}
      <div className={clsx("flex min-h-0 flex-1 flex-col", !noPad && "p-4", bodyClassName)}>
        {children}
      </div>
    </section>
  );
}

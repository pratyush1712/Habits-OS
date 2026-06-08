import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-12 w-full min-w-0 appearance-none border-2 border-slate-950 bg-white px-3 py-2 font-sans text-lg font-black text-slate-950 transition-colors outline-none file:inline-flex file:h-8 file:border-0 file:bg-transparent file:text-sm file:font-black file:text-foreground placeholder:text-slate-500 focus-visible:border-blue-700 focus-visible:ring-4 focus-visible:ring-yellow-300 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-red-500",
        className,
      )}
      {...props}
    />
  );
}

export { Input };

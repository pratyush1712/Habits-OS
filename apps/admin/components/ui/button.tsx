import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-none border-2 border-slate-950 font-sans font-black tracking-wide whitespace-nowrap no-underline transition-colors outline-none select-none active:translate-y-0.5 focus-visible:ring-4 focus-visible:ring-yellow-300 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-blue-600 text-white hover:bg-blue-500",
        outline:
          "bg-white text-slate-950 hover:bg-yellow-200 aria-expanded:bg-yellow-200 aria-expanded:text-slate-950",
        secondary:
          "bg-green-400 text-slate-950 hover:bg-green-300 aria-expanded:bg-green-300 aria-expanded:text-slate-950",
        ghost:
          "bg-yellow-200 text-slate-950 hover:bg-green-300 aria-expanded:bg-green-300 aria-expanded:text-slate-950",
        destructive:
          "bg-red-500 text-white hover:bg-red-400 focus-visible:ring-yellow-300",
        link: "border-transparent bg-transparent px-0 text-blue-700 underline decoration-2 underline-offset-4 hover:text-blue-900",
      },
      size: {
        default:
          "min-h-11 gap-2 px-4 py-2 text-sm uppercase has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        xs: "min-h-9 gap-1 px-3 py-1.5 text-xs uppercase [&_svg:not([class*='size-'])]:size-3",
        sm: "min-h-10 gap-1 px-3 py-2 text-xs uppercase",
        lg: "min-h-14 gap-2 px-6 py-3 text-lg uppercase",
        icon: "size-11",
        "icon-xs": "size-9 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-10",
        "icon-lg": "size-14",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };

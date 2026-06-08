import * as React from "react";

import { cn } from "@/lib/utils";

function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div data-slot="table-container" className="relative w-full overflow-x-auto border-4 border-slate-950 bg-white">
      <table data-slot="table" className={cn("w-full caption-bottom border-collapse text-base font-bold", className)} {...props} />
    </div>
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return <thead data-slot="table-header" className={cn("bg-slate-950 text-white [&_tr]:border-b-4 [&_tr]:border-slate-950", className)} {...props} />;
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" className={cn("[&_tr:last-child]:border-b-0", className)} {...props} />;
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return <tfoot data-slot="table-footer" className={cn("border-t-4 border-slate-950 bg-yellow-200 font-black", className)} {...props} />;
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return <tr data-slot="table-row" className={cn("border-b-2 border-slate-950 transition-colors hover:bg-yellow-100 data-[state=selected]:bg-blue-100", className)} {...props} />;
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return <th data-slot="table-head" className={cn("h-12 border-r-2 border-slate-950 px-3 text-left align-middle text-sm font-black tracking-wide whitespace-nowrap uppercase last:border-r-0 [&:has([role=checkbox])]:pr-0", className)} {...props} />;
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return <td data-slot="table-cell" className={cn("border-r-2 border-slate-950 p-3 align-middle whitespace-nowrap last:border-r-0 [&:has([role=checkbox])]:pr-0", className)} {...props} />;
}

function TableCaption({ className, ...props }: React.ComponentProps<"caption">) {
  return <caption data-slot="table-caption" className={cn("mt-4 text-base font-black text-slate-700", className)} {...props} />;
}

export { Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption };

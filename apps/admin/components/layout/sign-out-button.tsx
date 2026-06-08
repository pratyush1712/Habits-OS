"use client";

import { signOut } from "next-auth/react";

/**
 * Client-side sign-out control for the private shell.
 */
export function SignOutButton() {
  return (
    <button
      className="inline-flex min-h-11 items-center justify-center border-2 border-slate-950 bg-red-600 px-4 py-2 text-sm font-black text-white transition-transform hover:bg-red-500 active:translate-y-0.5"
      onClick={() => {
        void signOut({ callbackUrl: "/" });
      }}
      type="button"
    >
      Sign out
    </button>
  );
}

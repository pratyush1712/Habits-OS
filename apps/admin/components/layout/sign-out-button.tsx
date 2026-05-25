"use client";

import { signOut } from "next-auth/react";

import { Button } from "@/components/ui/button";

/**
 * Client-side sign-out control for the private shell.
 */
export function SignOutButton() {
  return (
    <Button
      className="focus-ring"
      onClick={() => {
        void signOut({ callbackUrl: "/" });
      }}
      type="button"
      variant="outline"
    >
      Sign out
    </Button>
  );
}

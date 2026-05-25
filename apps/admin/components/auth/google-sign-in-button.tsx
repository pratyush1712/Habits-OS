"use client";

import { signIn } from "next-auth/react";

import { Button } from "@/components/ui/button";

/**
 * Client-side Google sign-in trigger for the public login screen.
 */
export function GoogleSignInButton({
  callbackUrl,
  enabled,
}: {
  callbackUrl: string;
  enabled: boolean;
}) {
  return (
    <Button
      className="focus-ring h-11 min-w-[220px]"
      disabled={!enabled}
      onClick={() => {
        void signIn("google", { callbackUrl });
      }}
      type="button"
      variant="default"
    >
      {enabled ? "Continue with Google" : "Google auth not configured"}
    </Button>
  );
}

import type { Role } from "@/types/auth";

/** Mirrors the backend's `require_role(Role.ADMIN)` check (OWNER/ADMIN can write, MEMBER is read-only). */
export function canWrite(role: Role | undefined): boolean {
  return role === "owner" || role === "admin";
}

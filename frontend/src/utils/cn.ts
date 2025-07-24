/**
 * Utility function to merge CSS classes
 * Simple implementation without external dependencies
 */
export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ');
}

/**
 * Pure tab-cycling logic, separated from React so it can be unit-tested.
 *
 * `direction` is +1 for next, -1 for previous. Wraps around.
 */
export function cycleTab(ids: string[], active: string, direction: 1 | -1): string {
  if (ids.length === 0) return active;
  const idx = ids.indexOf(active);
  if (idx === -1) return ids[0];
  const next = (idx + direction + ids.length) % ids.length;
  return ids[next];
}

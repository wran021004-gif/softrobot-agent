import { join } from 'node:path';
import lockfile from 'proper-lockfile';

export function acquireRuntimeLock(directory, onCompromised) {
  // proper-lockfile indexes its in-process locks by target path, not lockfilePath.
  // The DevKit locks the directory itself: use a distinct target for this lifetime lock.
  return lockfile.lock(join(directory, '.gateway-runtime-owner'), {
    realpath: false, lockfilePath: join(directory, '.gateway-runtime.lock'),
    stale: 30_000, update: 10_000, onCompromised,
  });
}

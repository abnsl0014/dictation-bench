/**
 * Backport of electron-builder #9769 ("fix(nsis): safely copy UserProgramFiles path",
 * shipped in electron-builder 26.12.0) into the app-builder-lib we build with (24.13.3).
 *
 * The bug: on a fresh per-user install (no InstallLocation in HKCU yet, i.e. every new
 * customer) templates/nsis/multiUser.nsh reads the folder path returned by
 * SHGetKnownFolderPath with
 *     System::Call '*$2(&w${NSIS_MAX_STRLEN} .s)'
 * which copies a fixed NSIS_MAX_STRLEN wide chars out of a buffer that is usually a few
 * dozen bytes long. When that over-read crosses into unmapped memory the installer dies
 * before showing a window: System.dll, exception 0xc0000005, fault offset 0x00001581.
 * Whether it crashes depends on heap layout, so it is intermittent; on the first signed
 * 0.5.11 build it hit about half of the launches from SmartScreen's "Run anyway".
 *
 * The fix copies the path with lstrcpynW (bounded, stops at the terminator) and frees
 * the buffer whenever one was returned, exactly as upstream does.
 *
 * Runs before electron-builder in `npm run dist:win`. Idempotent. Fails the build if the
 * template is neither the known buggy version nor already fixed, so an electron-builder
 * upgrade can't silently drop or mangle the fix (26.12.0+ already contains it and is
 * reported as "already fixed").
 */
const fs = require('fs');
const path = require('path');

const template = path.join(
  path.dirname(require.resolve('app-builder-lib/package.json')),
  'templates',
  'nsis',
  'multiUser.nsh',
);

const BUGGY = [
  '      System::Store S',
  '      # Win7 has a per-user programfiles known folder and this can be a non-default location',
  "      System::Call 'SHELL32::SHGetKnownFolderPath(g \"${FOLDERID_UserProgramFiles}\", i ${KF_FLAG_CREATE}, p 0, *p .r2)i.r1'",
  '      ${If} $1 == 0',
  "        System::Call '*$2(&w${NSIS_MAX_STRLEN} .s)'",
  '        StrCpy $0 $1',
  "        System::Call 'OLE32::CoTaskMemFree(p r2)'",
  '      ${endif}',
  '      System::Store L',
];

const FIXED = [
  '      Push $1',
  '      Push $2',
  '      # UserProgramFiles is the per-user install root and can be a non-default location',
  '      # (bounded copy: backport of electron-builder #9769, see scripts/patchNsisMultiUser.js)',
  '      StrCpy $2 0',
  "      System::Call 'SHELL32::SHGetKnownFolderPath(g \"${FOLDERID_UserProgramFiles}\", i ${KF_FLAG_CREATE}, p 0, *p .r2)i.r1'",
  '      ${If} $1 == 0',
  "        System::Call 'KERNEL32::lstrcpynW(w .r0, p r2, i ${NSIS_MAX_STRLEN})p'",
  '      ${endif}',
  '      # SHGetKnownFolderPath may return allocated memory even on failure',
  '      ${If} $2 != 0',
  "        System::Call 'OLE32::CoTaskMemFree(p r2)'",
  '      ${endif}',
  '      Pop $2',
  '      Pop $1',
];

const src = fs.readFileSync(template, 'utf8');
const eol = src.includes('\r\n') ? '\r\n' : '\n';
const buggy = BUGGY.join(eol);
const fixed = FIXED.join(eol);
const rel = path.relative(process.cwd(), template);

if (src.includes("KERNEL32::lstrcpynW(w .r0, p r2")) {
  console.log(`  • ${rel}: UserProgramFiles copy already bounded (lstrcpynW) — nothing to do`);
} else if (src.includes(buggy)) {
  const out = src.replace(buggy, fixed);
  if (out.includes('&w${NSIS_MAX_STRLEN} .s')) {
    throw new Error(`${rel}: patch applied but the unbounded read is still present`);
  }
  fs.writeFileSync(template, out);
  console.log(`  • ${rel}: patched the unbounded UserProgramFiles read (electron-builder #9769 backport)`);
} else {
  throw new Error(
    `${rel}: unexpected multiUser.nsh — neither the known buggy block nor the lstrcpynW fix was found. ` +
      'Check whether this electron-builder version still has the System.dll+0x1581 over-read before building.',
  );
}

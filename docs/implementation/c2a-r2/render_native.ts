/** Read-only Sign export renderer; writes only the provided Send evidence directory. */
import fs from 'node:fs';
import path from 'node:path';
import { insertFieldInPDFV2 } from '/root/worktrees/sign-c1b/packages/lib/server-only/pdf/insert-field-in-pdf-v2';

async function main() {
  const output = path.resolve(process.argv[2]);
  const fields = JSON.parse(fs.readFileSync(path.join(output, 'harbor-native-fields.json'), 'utf8'));
  process.chdir('/root/worktrees/sign-c1b/apps/remix');
  for (const mode of ['before', 'after']) {
    const rendered = fields[mode].map((field: any, i: number) => ({
      ...field, id: i + 1, inserted: true,
      customText: field.type === 'DATE' ? (mode === 'before' ? '2026-11-15 04:23 PM' : '2026-11-15') : '',
      signature: field.type === 'SIGNATURE' ? { typedSignature: 'Lee Harbor', signatureImageAsBase64: null } : null,
    }));
    const pdf = await insertFieldInPDFV2({pageWidth: 612, pageHeight: 792, fields: rendered});
    fs.writeFileSync(path.join(output, `harbor-${mode}-native.pdf`), pdf);
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });

import { createHash } from 'node:crypto';
import { registerHooks } from 'node:module';

export const MAIN_SHA256 = 'c6902760304c303edec52e2894370be68ca6d679ca20f922a589c6fbc416f9c0';
export const SKILL_MOUNTER_SHA256 = '0d1d64ec1d2f0d01eec22c534ffb40728274d8c06d1959229db7684735999d91';

// Fail closed on upstream changes. This transforms the pinned server in memory;
// npm files and the native approval/agent engine are never edited.
export function extendTrueForge(source) {
  if (createHash('sha256').update(source).digest('hex') !== MAIN_SHA256) {
    throw new Error('Unsupported TrueForge build: review the E2B compatibility extension');
  }
  const replace = (before, after) => {
    if (source.split(before).length !== 2) throw new Error('TrueForge E2B patch anchor changed');
    source = source.replace(before, after);
  };
  replace('var SandboxProviderManifestSchema = DaytonaSandboxProviderSchema.openapi("SandboxProviderManifest");',
    `var E2BSandboxProviderSchema = z12.object({
      type: z12.literal("e2b"), auth: DaytonaSandboxProviderAuthSchema,
      template: z12.string().min(1).default("base"),
      exec_timeout_ms: z12.number().int().min(1).max(20000),
      lifetime_ms: z12.number().int().min(60000).max(3600000)
    }).strict();
    var SandboxProviderManifestSchema = z12.discriminatedUnion("type", [
      DaytonaSandboxProviderSchema, E2BSandboxProviderSchema
    ]).openapi("SandboxProviderManifest");`);
  replace('  DaytonaSandboxProviderSchema,\n  TrueFoundrySandboxProviderSchema',
    '  DaytonaSandboxProviderSchema,\n  E2BSandboxProviderSchema,\n  TrueFoundrySandboxProviderSchema');
  replace('  const { apiKey, ...settings } = toDaytonaSandboxProviderInput(manifest);',
    `  if (manifest.type === "e2b") return new E2BSandboxProvider({
      apiKey: manifest.auth.api_key, tenantName: tenant_id,
      template: manifest.template, timeoutMs: manifest.exec_timeout_ms,
      lifetimeMs: manifest.lifetime_ms
    });\n  const { apiKey, ...settings } = toDaytonaSandboxProviderInput(manifest);`);
  replace('  switch (record.manifest.type) {\n    case "daytona":',
    '  switch (record.manifest.type) {\n    case "e2b":\n    case "daytona":');
  replace('if (record?.manifest.type !== "daytona")',
    'if (!["daytona", "e2b"].includes(record?.manifest.type))');
  replace('existing?.manifest.type === "daytona" ? existing.manifest.auth.api_key : void 0',
    'existing?.manifest.type === incoming.type ? existing.manifest.auth.api_key : void 0');
  replace('DaytonaSandboxProviderSchema.omit({ auth: true }).strict().openapi("CatalogSandboxProvider")',
    'z12.union([DaytonaSandboxProviderSchema.omit({ auth: true }), E2BSandboxProviderSchema.omit({ auth: true })]).openapi("CatalogSandboxProvider")');
  return `import { E2BSandboxProvider } from ${JSON.stringify(new URL('./e2b-provider.mjs', import.meta.url).href)};\n` + source;
}

export function extendSkillMounter(source) {
  if (createHash('sha256').update(source).digest('hex') !== SKILL_MOUNTER_SHA256) {
    throw new Error('Unsupported TrueForge SkillMounter build: review the no-skills extension');
  }
  const before = '  getSandboxInit(paths) {\n    return {';
  const after = '  getSandboxInit(paths) {\n    if (this.skills.length === 0) return null;\n    return {';
  if (source.split(before).length !== 2) {
    throw new Error('TrueForge SkillMounter patch anchor changed');
  }
  return source.replace(before, after);
}

export function installE2BHook() {
  const mainTarget = new URL('../node_modules/@truefoundry/trueforge/dist/main.js', import.meta.url).href;
  const skillTarget = new URL(
    '../node_modules/@truefoundry/trueforge-core/dist/core/sandbox/skills/SkillMounter.mjs',
    import.meta.url,
  ).href;
  return registerHooks({
    load(url, context, nextLoad) {
      const result = nextLoad(url, context);
      if (url === mainTarget) {
        return { ...result, source: extendTrueForge(Buffer.from(result.source).toString('utf8')) };
      }
      if (url === skillTarget) {
        return { ...result, source: extendSkillMounter(Buffer.from(result.source).toString('utf8')) };
      }
      return result;
    },
  });
}

const { notarize } = require('@electron/notarize');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir, packager } = context;
  if (electronPlatformName !== 'darwin') return;

  const appName = packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  // Prefer API key (p8) — works on local MacBook and CI
  if (process.env.APPLE_API_KEY_PATH && process.env.APPLE_API_KEY_ID && process.env.APPLE_API_ISSUER) {
    console.log(`[notarize] Submitting ${appName}.app via API key…`);
    await notarize({
      tool: 'notarytool',
      appPath,
      appleApiKey:     process.env.APPLE_API_KEY_PATH,
      appleApiKeyId:   process.env.APPLE_API_KEY_ID,
      appleApiIssuer:  process.env.APPLE_API_ISSUER,
    });
    console.log('[notarize] Done ✓');
    return;
  }

  // Fallback: Apple ID + app-specific password (GitHub Actions)
  if (process.env.APPLE_ID && process.env.APPLE_APP_SPECIFIC_PASSWORD) {
    console.log(`[notarize] Submitting ${appName}.app via Apple ID…`);
    await notarize({
      tool: 'notarytool',
      appPath,
      appleId:         process.env.APPLE_ID,
      appleIdPassword: process.env.APPLE_APP_SPECIFIC_PASSWORD,
      teamId:          process.env.APPLE_TEAM_ID,
    });
    console.log('[notarize] Done ✓');
    return;
  }

  console.log('[notarize] No credentials set — skipping notarization');
};

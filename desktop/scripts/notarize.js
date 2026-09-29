/**
 * afterSign hook for electron-builder.
 * Submits the signed .app to Apple's notarization service.
 * Requires env: APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, APPLE_TEAM_ID
 */
const { notarize } = require('@electron/notarize');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir, packager } = context;

  if (electronPlatformName !== 'darwin') return;

  // Skip notarization if credentials are not set
  if (!process.env.APPLE_ID || !process.env.APPLE_APP_SPECIFIC_PASSWORD) {
    console.log('[notarize] Credentials not set — skipping notarization');
    return;
  }

  const appName = packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.log(`[notarize] Submitting ${appName}.app to Apple…`);

  await notarize({
    appBundleId: 'cloud.k-creative.studio',
    appPath,
    appleId:           process.env.APPLE_ID,
    appleIdPassword:   process.env.APPLE_APP_SPECIFIC_PASSWORD,
    teamId:            process.env.APPLE_TEAM_ID,
  });

  console.log('[notarize] Done ✓');
};

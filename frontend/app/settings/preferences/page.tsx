import { SettingsLayout } from "@/components/settings/SettingsLayout";
import { PreferencesSettingsClient } from "@/components/settings/PreferencesSettingsClient";

export const metadata = { title: "Preferences — Stock Analyst" };

export default function PreferencesSettingsPage() {
  return (
    <SettingsLayout>
      <PreferencesSettingsClient />
    </SettingsLayout>
  );
}

import { SettingsLayout } from "@/components/settings/SettingsLayout";
import { PrivacySettingsClient } from "@/components/settings/PrivacySettingsClient";

export const metadata = { title: "Privacy Settings — Stock Analyst" };

export default function PrivacySettingsPage() {
  return (
    <SettingsLayout>
      <PrivacySettingsClient />
    </SettingsLayout>
  );
}

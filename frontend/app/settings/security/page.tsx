import { SettingsLayout } from "@/components/settings/SettingsLayout";
import { SecuritySettingsClient } from "@/components/settings/SecuritySettingsClient";

export const metadata = { title: "Security Settings — Stock Analyst" };

export default function SecuritySettingsPage() {
  return (
    <SettingsLayout>
      <SecuritySettingsClient />
    </SettingsLayout>
  );
}

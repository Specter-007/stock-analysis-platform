import { SettingsLayout } from "@/components/settings/SettingsLayout";
import { AccountSettingsClient } from "@/components/settings/AccountSettingsClient";

export const metadata = { title: "Account Settings — Stock Analyst" };

export default function AccountSettingsPage() {
  return (
    <SettingsLayout>
      <AccountSettingsClient />
    </SettingsLayout>
  );
}

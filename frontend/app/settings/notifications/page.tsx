import { SettingsLayout } from "@/components/settings/SettingsLayout";
import { NotificationsSettingsClient } from "@/components/settings/NotificationsSettingsClient";

export const metadata = { title: "Notification Settings — Stock Analyst" };

export default function NotificationsSettingsPage() {
  return (
    <SettingsLayout>
      <NotificationsSettingsClient />
    </SettingsLayout>
  );
}

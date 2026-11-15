"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useAuth } from "@/components/AuthContext";
import { Avatar } from "@/components/Avatar";
import { ErrorText, SuccessText } from "@/components/ErrorText";
import { Field } from "@/components/Field";
import { RequireAuth } from "@/components/RequireAuth";
import { authApi, errorMessage, usersApi } from "@/lib/api";
import { cardClass, dangerButton, inputClass, primaryButton, secondaryButton } from "@/lib/ui";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={`${cardClass} space-y-3 p-4`}>
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function SettingsContent() {
  const { user, setUser, logout } = useAuth();
  const router = useRouter();

  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [profileMsg, setProfileMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [dangerPassword, setDangerPassword] = useState("");
  const [confirmUsername, setConfirmUsername] = useState("");
  const [dangerError, setDangerError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name);
      setBio(user.bio ?? "");
    }
  }, [user]);

  if (!user) return null;

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setProfileMsg(null);
    try {
      setUser(await usersApi.update({ display_name: displayName, bio }));
      setProfileMsg({ ok: true, text: "Profile saved." });
    } catch (caught) {
      setProfileMsg({ ok: false, text: errorMessage(caught) });
    }
  };

  const changeAvatar = async (file: File | undefined) => {
    if (!file) return;
    setProfileMsg(null);
    try {
      setUser(await usersApi.uploadAvatar(file));
      setProfileMsg({ ok: true, text: "Photo updated." });
    } catch (caught) {
      setProfileMsg({ ok: false, text: errorMessage(caught) });
    }
  };

  const changePassword = async (event: FormEvent) => {
    event.preventDefault();
    setPasswordMsg(null);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setPasswordMsg({ ok: true, text: "Password changed. Other devices were logged out." });
    } catch (caught) {
      setPasswordMsg({ ok: false, text: errorMessage(caught) });
    }
  };

  const leave = async (action: () => Promise<void>) => {
    setDangerError(null);
    try {
      await action();
      await logout().catch(() => undefined);
      router.push("/login");
    } catch (caught) {
      setDangerError(errorMessage(caught));
    }
  };

  const passwordForDanger = user.has_password ? dangerPassword : null;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Settings</h1>

      <Section title="Profile">
        <div className="flex items-center gap-3">
          <Avatar name={user.display_name} src={user.avatar_url} size="lg" />
          <label className={`${secondaryButton} cursor-pointer`}>
            Change photo
            <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => changeAvatar(e.target.files?.[0])} />
          </label>
        </div>
        <form onSubmit={saveProfile} className="space-y-3">
          <Field label="Display name" id="display_name" required maxLength={50} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          <div className="space-y-1">
            <label htmlFor="bio" className="block text-sm font-medium text-ink">Bio</label>
            <textarea id="bio" rows={3} maxLength={300} value={bio} onChange={(e) => setBio(e.target.value)} className={inputClass} />
          </div>
          {profileMsg && (profileMsg.ok ? <SuccessText message={profileMsg.text} /> : <ErrorText message={profileMsg.text} />)}
          <button type="submit" className={primaryButton}>Save</button>
        </form>
      </Section>

      <Section title="Account">
        <p className="text-sm text-muted">
          {user.email} · {user.is_email_verified ? "verified ✓" : "not verified"}
        </p>
        {!user.is_email_verified && (
          <button className="text-sm font-semibold text-brand" onClick={() => authApi.resendVerification(user.email)}>
            Send verification email
          </button>
        )}
      </Section>

      <Section title="Change password">
        {user.has_password ? (
          <form onSubmit={changePassword} className="space-y-3">
            <Field label="Current password" id="current_password" type="password" autoComplete="current-password" required value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            <Field label="New password" id="new_password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            {passwordMsg && (passwordMsg.ok ? <SuccessText message={passwordMsg.text} /> : <ErrorText message={passwordMsg.text} />)}
            <button type="submit" className={primaryButton}>Change password</button>
          </form>
        ) : (
          <p className="text-sm text-muted">You signed in with Google. Use “Forgot password” on the login page to create a password.</p>
        )}
      </Section>

      <Section title="Sessions">
        <button className={secondaryButton} onClick={() => leave(authApi.logoutAll)}>Log out of all devices</button>
      </Section>

      <Section title="Danger zone">
        <ErrorText message={dangerError} />
        {user.has_password && (
          <Field label="Your password" id="danger_password" type="password" autoComplete="current-password" value={dangerPassword} onChange={(e) => setDangerPassword(e.target.value)} />
        )}
        <div className="space-y-2">
          <p className="text-sm text-muted">Deactivating hides your profile and posts. Logging in again brings them back.</p>
          <button className={secondaryButton} onClick={() => leave(() => authApi.deactivate(passwordForDanger))}>Deactivate account</button>
        </div>
        <div className="space-y-2 border-t border-line pt-3">
          <p className="text-sm text-muted">Deleting is permanent: your posts, comments and photos are removed.</p>
          <Field label={`Type your username (${user.username}) to confirm`} id="confirm_username" value={confirmUsername} onChange={(e) => setConfirmUsername(e.target.value)} />
          <button
            className={dangerButton}
            disabled={confirmUsername.trim().toLowerCase() !== user.username}
            onClick={() => leave(() => authApi.deleteAccount(passwordForDanger, confirmUsername.trim().toLowerCase()))}
          >
            Delete my account
          </button>
        </div>
      </Section>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
      <SettingsContent />
    </RequireAuth>
  );
}

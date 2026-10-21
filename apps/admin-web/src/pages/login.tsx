import { Gauge, LogIn } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Input, Label } from "@/components/ui";
import { API_BASE, setToken } from "@/lib/api";

export function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const devLogin = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/me`);
      if (!res.ok) throw new Error("Geliştirici girişi bu ortamda kapalı (DEV_AUTH_BYPASS).");
      setToken("dev");
      navigate("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-surface p-4">
      <Card className="w-full max-w-sm p-6">
        <div className="mb-5 flex items-center gap-2">
          <Gauge className="size-7 text-primary" aria-hidden="true" />
          <div>
            <h1 className="text-lg font-bold">Mağaza Asistanım</h1>
            <p className="text-sm text-muted">Yönetim paneline giriş</p>
          </div>
        </div>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setError("E-posta ile giriş Firebase Auth yapılandırması gerektirir (üretim ortamı).");
          }}
        >
          <div>
            <Label htmlFor="email">E-posta</Label>
            <Input id="email" type="email" autoComplete="username" />
          </div>
          <div>
            <Label htmlFor="password">Şifre</Label>
            <Input id="password" type="password" autoComplete="current-password" />
          </div>
          <Button type="submit" variant="outline" className="w-full">
            Giriş yap
          </Button>
        </form>
        <div className="my-4 flex items-center gap-2 text-xs text-muted">
          <span className="h-px flex-1 bg-line" /> yerel geliştirme <span className="h-px flex-1 bg-line" />
        </div>
        <Button className="w-full" onClick={devLogin} data-testid="dev-login">
          <LogIn aria-hidden="true" /> Geliştirici olarak giriş
        </Button>
        {error ? (
          <p className="mt-3 text-sm text-bad" role="alert">
            {error}
          </p>
        ) : null}
      </Card>
    </div>
  );
}

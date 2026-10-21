import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { Layout } from "./components/layout";
import "./index.css";
import { getToken } from "./lib/api";
import { FiltersProvider } from "./lib/state";
import { ConversationsPage } from "./pages/conversations";
import { DemandPage } from "./pages/demand";
import { ExecutivePage } from "./pages/executive";
import { FunnelPage } from "./pages/funnel";
import { LoginPage } from "./pages/login";
import { ProductsPage } from "./pages/products";
import { QualityPage } from "./pages/quality";
import { SettingsPage } from "./pages/settings";
import { UnmetPage } from "./pages/unmet";
import { UsagePage } from "./pages/usage";

function RequireAuth() {
  return getToken() ? <Layout /> : <Navigate to="/giris" replace />;
}

const router = createBrowserRouter([
  { path: "/giris", element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: "/", element: <ExecutivePage /> },
      { path: "/huni", element: <FunnelPage /> },
      { path: "/talepler", element: <DemandPage /> },
      { path: "/karsilanmayan", element: <UnmetPage /> },
      { path: "/urunler", element: <ProductsPage /> },
      { path: "/kalite", element: <QualityPage /> },
      { path: "/kullanim", element: <UsagePage /> },
      { path: "/konusmalar", element: <ConversationsPage /> },
      { path: "/ayarlar", element: <SettingsPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1, refetchOnWindowFocus: false } } });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <FiltersProvider>
        <RouterProvider router={router} />
      </FiltersProvider>
    </QueryClientProvider>
  </StrictMode>,
);

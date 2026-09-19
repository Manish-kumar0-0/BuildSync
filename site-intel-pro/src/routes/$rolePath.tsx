import { createFileRoute } from "@tanstack/react-router";

import { ConstructionApp } from "./index";

export const Route = createFileRoute("/$rolePath")({
  component: ConstructionApp,
});

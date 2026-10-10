import { defineRailway, project, service } from "railway/iac";

// solo-habits: the habits cell. Variables stay unmanaged (secrets live in Railway only).
// habits-api sleeps when idle (Railway Serverless) and wakes on the next request;
// habits-publisher is a cron sweep of the outbox that exits after each run.
export default defineRailway(() => {
  const api = service("habits-api", {
    healthcheck: "/health",
    healthcheckTimeout: 60,
    deploy: { sleepApplication: true },
  });
  const publisher = service("habits-publisher", {
    startCommand: "habits-publish",
    deploy: { cronSchedule: "*/15 * * * *", restartPolicyType: "NEVER" },
  });

  return project("solo-habits", {
    variables: { managed: false },
    resources: [api, publisher],
  });
});

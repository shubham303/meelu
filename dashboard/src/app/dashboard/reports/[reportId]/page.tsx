"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Download, Pencil, Sparkles, Trash2 } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Button, Card, ConfirmDelete, Field, IconButton, Input, Modal, PageHeader, Spinner } from "@/components/ui";
import { ChartFrame } from "@/components/agent/chart-frame";
import { api, useApi } from "@/lib/use-api";
import { formatRelative } from "@/lib/utils";
import { REPORT_DESK_LABEL } from "@/features/reports/desks";
import { useIsApp } from "@/lib/use-app-mode";
import { useAgentTasks } from "../../agent-tasks";
import type { Report } from "@/lib/types";

function fileName(title: string): string {
  return `${title.replace(/[^\w -]+/g, "").trim() || "report"}.html`;
}

export default function ReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const router = useRouter();
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const { data: report, loading, error, refresh } = useApi<Report>(
    `/api/v1/reports/${reportId}`,
  );
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (loading) return <Spinner />;
  if (error || !report) {
    return (
      <PageEnter>
        <BackLink />
        <p className="text-sm text-bad">{error ?? "This report is gone."}</p>
      </PageEnter>
    );
  }

  const saveFile = async () => {
    setActionError(null);
    setNotice(null);
    const save = window.meeluAgent?.saveTextFile;
    if (save) {
      const done = await save({ name: fileName(report.title), content: report.html });
      if ("error" in done) setActionError(done.error);
      else if (done.path) setNotice(`Saved to ${done.path}`);
      return;
    }
    const url = URL.createObjectURL(new Blob([report.html], { type: "text/html" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName(report.title);
    a.click();
    URL.revokeObjectURL(url);
  };

  const rename = async () => {
    const next = title.trim();
    if (!next) return;
    setActionError(null);
    try {
      await api(`/api/v1/reports/${report.id}`, { method: "PUT", body: { title: next } });
      setRenaming(false);
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not rename the report");
    }
  };

  return (
    <PageEnter>
      <BackLink />
      <PageHeader
        title={report.title}
        description={`${REPORT_DESK_LABEL[report.desk]} · saved ${formatRelative(report.createdAt)}${
          report.updatedAt !== report.createdAt ? ` · changed ${formatRelative(report.updatedAt)}` : ""
        } · by ${report.createdBy === "agent" ? "Meelu" : "you"}`}
        actions={
          <>
            {isApp && (
              <IconButton
                title="Ask Meelu about this report"
                aria-label="Ask Meelu about this report"
                className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
                onClick={() =>
                  launchTask({
                    title: `Report: ${report.title}`,
                    endpoint: "/api/agent/ask-report",
                    emptyHint: "Ask about this report, or say how to change it. It reads only your saved reports.",
                    draft: { report: `"${report.title}" (id ${report.id})` },
                    onWrote: () => refresh(),
                  })
                }
              >
                <Sparkles size={16} />
              </IconButton>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setTitle(report.title);
                setRenaming(true);
              }}
            >
              <Pencil size={13} /> Rename
            </Button>
            <Button variant="outline" size="sm" onClick={() => void saveFile()}>
              <Download size={13} /> Save as file
            </Button>
            <Button variant="danger" size="sm" onClick={() => setDeleting(true)}>
              <Trash2 size={13} /> Delete
            </Button>
          </>
        }
      />
      {notice && <p className="text-sm text-good mb-3">{notice}</p>}
      {actionError && <p className="text-sm text-bad mb-3">{actionError}</p>}

      <Card className="overflow-hidden p-0">
        <ChartFrame html={report.html} title={report.title} />
      </Card>

      <Modal open={renaming} onClose={() => setRenaming(false)} title="Rename report">
        <div className="space-y-4">
          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setRenaming(false)}>
              Cancel
            </Button>
            <Button disabled={!title.trim()} onClick={() => void rename()}>
              Save
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDelete
        open={deleting}
        onClose={() => setDeleting(false)}
        what="this report"
        onConfirm={async () => {
          await api(`/api/v1/reports/${report.id}`, { method: "DELETE" });
          router.push("/dashboard/reports");
        }}
      />
    </PageEnter>
  );
}

function BackLink() {
  return (
    <Link
      href="/dashboard/reports"
      className="mb-4 inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
    >
      <ArrowLeft size={14} /> Reports
    </Link>
  );
}

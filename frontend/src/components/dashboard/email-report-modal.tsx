'use client'

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { AlertCircle, CheckCircle2, Download, FileText, Mail, Send } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { api } from '@/lib/api'
import type { Placement } from '@/lib/types'

interface EmailReportModalProps {
  placement: Placement | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EmailReportModal({ placement, open, onOpenChange }: EmailReportModalProps) {
  const [downloading, setDownloading] = useState(false)

  const emailStatusQuery = useQuery({
    queryKey: ['email-status'],
    queryFn: api.getEmailStatus,
    enabled: open,
  })

  const sendMutation = useMutation({
    mutationFn: (placementId: number) => api.emailBookingReport(placementId),
    onSuccess: (data) => {
      toast.success(`Playback report emailed successfully to ${data.to}`)
      onOpenChange(false)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to email report.')
    },
  })

  if (!placement) return null

  const clientEmail = placement.client?.email
  const clientName = placement.client?.name || placement.advertiser
  const isConfigured = emailStatusQuery.data?.is_configured ?? false

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await api.downloadBookingReport(placement.id)
      toast.success('Report downloaded.')
    } catch (err) {
      toast.error((err as Error).message || 'Could not download report.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="size-5 text-primary dark:text-brand" /> Email Campaign Report
          </DialogTitle>
          <DialogDescription>
            Dispatch an executive PDF proof-of-play report directly to the advertiser.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Recipient Card */}
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3.5 space-y-2 text-sm">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold text-foreground">{clientName}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {clientEmail ? clientEmail : <span className="text-amber-500 font-medium">No email address on client file</span>}
                </p>
              </div>
              <Badge variant="outline" className="text-[11px] font-mono">
                {placement.client?.client_code || 'Direct Booking'}
              </Badge>
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-border/40 text-xs text-muted-foreground">
              <FileText className="size-3.5 text-primary dark:text-brand shrink-0" />
              <span className="truncate">Attached: {placement.advertiser} - playback report.pdf</span>
            </div>
          </div>

          {/* SMTP Status Check */}
          {emailStatusQuery.isLoading ? (
            <div className="p-3 rounded-lg bg-muted animate-pulse text-xs text-muted-foreground">
              Checking email server connection...
            </div>
          ) : !isConfigured ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs space-y-1.5 text-amber-900 dark:text-amber-200">
              <div className="flex items-center gap-1.5 font-semibold">
                <AlertCircle className="size-4 text-amber-600 dark:text-amber-400 shrink-0" />
                SMTP Mailer Not Configured
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Direct email dispatch requires SMTP environment variables (<code className="font-mono text-foreground">SMTP_HOST</code>, <code className="font-mono text-foreground">SMTP_FROM</code>, <code className="font-mono text-foreground">SMTP_USER</code>, <code className="font-mono text-foreground">SMTP_PASSWORD</code>).
              </p>
              <p className="text-[11px] text-muted-foreground">
                You can download the PDF and send it via Gmail, Outlook, or WhatsApp in the meantime.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs flex items-center gap-2 text-emerald-800 dark:text-emerald-300">
              <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>Email service ready (sending via {emailStatusQuery.data?.sender})</span>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={handleDownload} disabled={downloading} className="gap-1.5 text-xs">
            <Download className="size-3.5" /> Download PDF
          </Button>

          <Button
            size="sm"
            onClick={() => sendMutation.mutate(placement.id)}
            disabled={!clientEmail || !isConfigured || sendMutation.isPending}
            className="gap-1.5 text-xs"
          >
            <Send className="size-3.5" />
            {sendMutation.isPending ? 'Sending...' : 'Send Email'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

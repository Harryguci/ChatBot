/**
 * Training detail page - Monitor individual training run with real-time updates.
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { trainingApi } from '@/lib/api/training';
import { useTrainingStatus } from '@/lib/hooks/useTrainingStatus';
import { useMetrics } from '@/lib/hooks/useMetrics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { StatusBadge } from '@/components/training/StatusBadge';
import { MetricsChart } from '@/components/training/MetricsChart';
import type { TrainingSummary } from '@/lib/types/training';
import { formatDate, formatRelativeTime, formatNumber } from '@/lib/utils/format';
import Link from 'next/link';

export default function TrainingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = parseInt(params.id as string);

  const [summary, setSummary] = useState<TrainingSummary | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const { status } = useTrainingStatus(runId, { enabled: true });
  const { metrics } = useMetrics(runId, { autoRefresh: true });

  // Fetch full training details
  useEffect(() => {
    async function fetchDetails() {
      try {
        const data = await trainingApi.getRun(runId);
        setSummary(data);
      } catch (error) {
        console.error('Error fetching training details:', error);
      } finally {
        setLoadingDetails(false);
      }
    }

    fetchDetails();
  }, [runId]);

  const handleStart = async () => {
    if (!confirm('Start this training run now?')) return;

    try {
      setActionLoading(true);
      await trainingApi.startTraining(runId);
      // Refresh details
      const data = await trainingApi.getRun(runId);
      setSummary(data);
    } catch (error) {
      console.error('Error starting training:', error);
      alert('Failed to start training run');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this training run?')) return;

    try {
      setActionLoading(true);
      await trainingApi.cancelTraining(runId);
      // Refresh details
      const data = await trainingApi.getRun(runId);
      setSummary(data);
    } catch (error) {
      console.error('Error canceling training:', error);
      alert('Failed to cancel training run');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (
      !confirm(
        'Are you sure you want to delete this training run? This action cannot be undone.'
      )
    )
      return;

    try {
      setActionLoading(true);
      await trainingApi.deleteRun(runId);
      router.push('/monitor');
    } catch (error) {
      console.error('Error deleting training:', error);
      alert('Failed to delete training run');
      setActionLoading(false);
    }
  };

  if (loadingDetails) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">
            Loading training details...
          </p>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="rounded-lg bg-red-50 p-6 dark:bg-red-950">
          <p className="text-red-600 dark:text-red-400">Training run not found</p>
          <Link href="/monitor">
            <Button variant="outline" className="mt-4">
              Back to Monitor
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Link href="/monitor">
              <Button variant="ghost" size="icon">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Button>
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {summary.run_name}
            </h1>
            <StatusBadge status={summary.status} />
          </div>
          <p className="mt-1 ml-14 text-gray-600 dark:text-gray-400">
            Run ID: {summary.run_id}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {summary.status === 'pending' && (
            <Button
              onClick={handleStart}
              disabled={actionLoading}
            >
              <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Start Training
            </Button>
          )}
          {summary.status === 'running' && (
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={actionLoading}
            >
              Cancel Training
            </Button>
          )}
          {summary.status !== 'running' && summary.status !== 'pending' && (
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading}
            >
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Progress Card (for running trainings) */}
      {summary.status === 'running' && status && (
        <Card>
          <CardHeader>
            <CardTitle>Training Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Overall Progress</span>
                <span className="font-medium">
                  Epoch {status.progress.current_epoch} of {status.progress.total_epochs} • Step{' '}
                  {status.progress.current_step}
                  {status.progress.max_steps && ` of ${status.progress.max_steps}`}
                </span>
              </div>
              <ProgressBar value={status.progress.percentage} />
            </div>

            {/* Current Metrics */}
            <div className="grid grid-cols-2 gap-4">
              {status.metrics.train_loss !== undefined && (
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Train Loss</p>
                  <p className="text-2xl font-bold">{formatNumber(status.metrics.train_loss, 4)}</p>
                </div>
              )}
              {status.metrics.eval_loss !== undefined && (
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Eval Loss</p>
                  <p className="text-2xl font-bold">{formatNumber(status.metrics.eval_loss, 4)}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Message */}
      {summary.error_message && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardHeader>
            <CardTitle className="text-red-700 dark:text-red-400">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-red-600 dark:text-red-400">{summary.error_message}</p>
          </CardContent>
        </Card>
      )}

      {/* Configuration Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Model & Dataset */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Model</p>
              <p className="font-medium">{summary.model_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Dataset</p>
              <p className="font-medium">{summary.dataset_name}</p>
            </div>
            {summary.output_dir && (
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Output Directory</p>
                <p className="font-mono text-sm">{summary.output_dir}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Timestamps */}
        <Card>
          <CardHeader>
            <CardTitle>Timeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Created</p>
              <p className="font-medium">
                {formatDate(summary.timestamps.created_at)}
              </p>
              <p className="text-xs text-gray-500">
                {formatRelativeTime(summary.timestamps.created_at)}
              </p>
            </div>
            {summary.timestamps.started_at && (
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Started</p>
                <p className="font-medium">
                  {formatDate(summary.timestamps.started_at)}
                </p>
                <p className="text-xs text-gray-500">
                  {formatRelativeTime(summary.timestamps.started_at)}
                </p>
              </div>
            )}
            {summary.timestamps.completed_at && (
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Completed</p>
                <p className="font-medium">
                  {formatDate(summary.timestamps.completed_at)}
                </p>
                <p className="text-xs text-gray-500">
                  {formatRelativeTime(summary.timestamps.completed_at)}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Hyperparameters */}
      <Card>
        <CardHeader>
          <CardTitle>Hyperparameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
            {Object.entries(summary.hyperparameters).map(([key, value]) => (
              <div key={key}>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {key.replace(/_/g, ' ')}
                </p>
                <p className="font-medium">
                  {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Metrics Chart */}
      {metrics.length > 0 && <MetricsChart metrics={metrics} />}
    </div>
  );
}

/**
 * Card component for displaying a training run summary.
 */

'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { StatusBadge } from './StatusBadge';
import { TrainingRun } from '@/lib/types/training';
import { formatDate, formatNumber } from '@/lib/utils/format';

interface TrainingCardProps {
  run: TrainingRun;
}

export function TrainingCard({ run }: TrainingCardProps) {
  return (
    <Link href={`/monitor/${run.id}`}>
      <Card className="cursor-pointer transition-shadow hover:shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle className="text-lg">{run.run_name}</CardTitle>
            <StatusBadge status={run.status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Model and Dataset Info */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">Model</p>
              <p className="font-medium">{run.model_name}</p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Dataset</p>
              <p className="font-medium">{run.dataset_name}</p>
            </div>
          </div>

          {/* Progress */}
          {run.status === 'running' && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Progress</span>
                <span className="font-medium">
                  Epoch {run.current_epoch} • Step {run.current_step}
                </span>
              </div>
              <ProgressBar value={run.progress_percentage} showLabel />
            </div>
          )}

          {/* Metrics */}
          {(run.train_loss || run.eval_loss) && (
            <div className="grid grid-cols-2 gap-2 text-sm">
              {run.train_loss !== undefined && (
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Train Loss</p>
                  <p className="font-medium">{formatNumber(run.train_loss, 4)}</p>
                </div>
              )}
              {run.eval_loss !== undefined && (
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Eval Loss</p>
                  <p className="font-medium">{formatNumber(run.eval_loss, 4)}</p>
                </div>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="text-xs text-gray-500 dark:text-gray-400">
            <p>Created: {formatDate(run.created_at)}</p>
            {run.started_at && <p>Started: {formatDate(run.started_at)}</p>}
            {run.completed_at && <p>Completed: {formatDate(run.completed_at)}</p>}
          </div>

          {/* Error Message */}
          {run.error_message && (
            <div className="rounded-md bg-red-50 p-2 dark:bg-red-950">
              <p className="text-xs text-red-600 dark:text-red-400">
                {run.error_message}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

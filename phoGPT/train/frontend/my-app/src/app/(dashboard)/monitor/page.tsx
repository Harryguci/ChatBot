/**
 * Monitor page - List all training runs with filtering.
 */

'use client';

import { useState } from 'react';
import { useTrainingRuns } from '@/lib/hooks/useTrainingRuns';
import { TrainingCard } from '@/components/training/TrainingCard';
import { Button } from '@/components/ui/Button';
import { TrainingStatus } from '@/lib/types/training';
import Link from 'next/link';

const statusFilters = [
  { label: 'All', value: undefined },
  { label: 'Running', value: TrainingStatus.RUNNING },
  { label: 'Completed', value: TrainingStatus.COMPLETED },
  { label: 'Failed', value: TrainingStatus.FAILED },
  { label: 'Pending', value: TrainingStatus.PENDING },
  { label: 'Cancelled', value: TrainingStatus.CANCELLED },
];

export default function MonitorPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const { runs, loading, error, refetch } = useTrainingRuns({
    status: statusFilter,
    autoRefresh: true,
  });

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">
            Loading training runs...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="rounded-lg bg-red-50 p-6 dark:bg-red-950">
          <p className="text-red-600 dark:text-red-400">Error: {error}</p>
          <Button onClick={refetch} variant="outline" className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Training Monitor
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Monitor all training runs and their progress
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={refetch} variant="outline">
            <svg
              className="mr-2 h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh
          </Button>
          <Link href="/create">
            <Button>
              <svg
                className="mr-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              New Training Run
            </Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {statusFilters.map((filter) => (
          <Button
            key={filter.label}
            variant={statusFilter === filter.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(filter.value)}
          >
            {filter.label}
          </Button>
        ))}
      </div>

      {/* Training Runs Grid */}
      {runs.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center dark:border-gray-700">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
            No training runs found
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {statusFilter
              ? 'No runs match the selected filter.'
              : 'Get started by creating a new training run.'}
          </p>
          {!statusFilter && (
            <div className="mt-6">
              <Link href="/create">
                <Button>Create Training Run</Button>
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
            Showing {runs.length} training run{runs.length !== 1 ? 's' : ''}
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {runs.map((run) => (
              <TrainingCard key={run.id} run={run} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

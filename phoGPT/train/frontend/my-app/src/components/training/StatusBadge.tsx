/**
 * Status badge component for training runs.
 */

'use client';

import { Badge } from '@/components/ui/Badge';
import { TrainingStatus } from '@/lib/types/training';
import { STATUS_LABELS } from '@/lib/utils/constants';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const getVariant = (status: string) => {
    switch (status) {
      case TrainingStatus.PENDING:
        return 'gray';
      case TrainingStatus.RUNNING:
        return 'blue';
      case TrainingStatus.COMPLETED:
        return 'success';
      case TrainingStatus.FAILED:
        return 'destructive';
      case TrainingStatus.CANCELLED:
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Badge variant={getVariant(status)} className={className}>
      {STATUS_LABELS[status] || status}
    </Badge>
  );
}

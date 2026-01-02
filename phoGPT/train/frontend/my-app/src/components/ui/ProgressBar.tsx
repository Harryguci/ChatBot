/**
 * Progress bar component for showing training progress.
 */

import * as React from 'react';
import { cn } from '@/lib/utils/cn';

interface ProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0-100
  showLabel?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

const ProgressBar = React.forwardRef<HTMLDivElement, ProgressBarProps>(
  ({ className, value, showLabel = true, variant = 'default', ...props }, ref) => {
    const percentage = Math.min(100, Math.max(0, value));

    const variantColors = {
      default: 'bg-blue-600 dark:bg-blue-500',
      success: 'bg-green-600 dark:bg-green-500',
      warning: 'bg-yellow-600 dark:bg-yellow-500',
      error: 'bg-red-600 dark:bg-red-500',
    };

    return (
      <div ref={ref} className={cn('w-full', className)} {...props}>
        <div className="relative h-4 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className={cn(
              'h-full transition-all duration-300 ease-in-out',
              variantColors[variant]
            )}
            style={{ width: `${percentage}%` }}
          />
          {showLabel && (
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
                {percentage.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }
);
ProgressBar.displayName = 'ProgressBar';

export { ProgressBar };

/**
 * Chart component for displaying training metrics over time.
 */

'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { TrainingMetric } from '@/lib/types/training';
import { CHART_COLORS } from '@/lib/utils/constants';

interface MetricsChartProps {
  metrics: TrainingMetric[];
  title?: string;
}

export function MetricsChart({ metrics, title = 'Training Metrics' }: MetricsChartProps) {
  // Transform metrics for recharts
  const chartData = metrics.map((metric) => ({
    step: metric.step,
    trainLoss: metric.loss,
    evalLoss: metric.eval_loss,
    learningRate: metric.learning_rate,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
            <XAxis
              dataKey="step"
              label={{ value: 'Step', position: 'insideBottom', offset: -5 }}
              className="text-sm"
            />
            <YAxis
              label={{ value: 'Loss', angle: -90, position: 'insideLeft' }}
              className="text-sm"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px',
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="trainLoss"
              stroke={CHART_COLORS.trainLoss}
              name="Train Loss"
              dot={false}
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="evalLoss"
              stroke={CHART_COLORS.evalLoss}
              name="Eval Loss"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

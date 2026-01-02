/**
 * Create Training Run page - Form to create new training runs.
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { trainingApi } from '@/lib/api/training';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { DEFAULT_HYPERPARAMETERS } from '@/lib/utils/constants';
import type { CreateTrainingRequest } from '@/lib/types/training';

// Validation schema
const trainingSchema = z.object({
  run_name: z.string().min(1, 'Run name is required').max(255),
  model_name: z.string().min(1, 'Model name is required'),
  dataset_name: z.string().min(1, 'Dataset name is required'),
  output_dir: z.string().optional(),
  notes: z.string().optional(),
  learning_rate: z.coerce.number().positive(),
  batch_size: z.coerce.number().int().positive(),
  num_epochs: z.coerce.number().int().positive(),
  warmup_steps: z.coerce.number().int().min(0),
  weight_decay: z.coerce.number().min(0).max(1),
  fp16: z.boolean(),
  bf16: z.boolean(),
  save_steps: z.coerce.number().int().positive(),
  eval_steps: z.coerce.number().int().positive(),
  logging_steps: z.coerce.number().int().positive(),
});

type TrainingFormData = z.infer<typeof trainingSchema>;

export default function CreateTrainingPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [autoStart, setAutoStart] = useState(true); // Auto-start by default

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TrainingFormData>({
    resolver: zodResolver(trainingSchema),
    defaultValues: {
      run_name: '',
      model_name: '',
      dataset_name: '',
      output_dir: '',
      notes: '',
      learning_rate: DEFAULT_HYPERPARAMETERS.learning_rate,
      batch_size: DEFAULT_HYPERPARAMETERS.batch_size,
      num_epochs: DEFAULT_HYPERPARAMETERS.num_epochs,
      warmup_steps: DEFAULT_HYPERPARAMETERS.warmup_steps,
      weight_decay: DEFAULT_HYPERPARAMETERS.weight_decay,
      fp16: DEFAULT_HYPERPARAMETERS.fp16,
      bf16: DEFAULT_HYPERPARAMETERS.bf16,
      save_steps: DEFAULT_HYPERPARAMETERS.save_steps,
      eval_steps: DEFAULT_HYPERPARAMETERS.eval_steps,
      logging_steps: DEFAULT_HYPERPARAMETERS.logging_steps,
    },
  });

  const onSubmit = async (data: TrainingFormData) => {
    try {
      setSubmitting(true);

      // Prepare request payload
      const payload: CreateTrainingRequest = {
        run_name: data.run_name,
        model_name: data.model_name,
        dataset_name: data.dataset_name,
        output_dir: data.output_dir || undefined,
        notes: data.notes || undefined,
        hyperparameters: {
          learning_rate: data.learning_rate,
          batch_size: data.batch_size,
          num_epochs: data.num_epochs,
          warmup_steps: data.warmup_steps,
          weight_decay: data.weight_decay,
          fp16: data.fp16,
          bf16: data.bf16,
          save_steps: data.save_steps,
          eval_steps: data.eval_steps,
          logging_steps: data.logging_steps,
          ...DEFAULT_HYPERPARAMETERS, // Include defaults for other fields
        },
      };

      const result = await trainingApi.createRun(payload);

      // Optionally start training automatically
      if (autoStart) {
        try {
          await trainingApi.startTraining(result.id);
          console.log(`Training run ${result.id} started automatically`);
        } catch (startError) {
          console.error('Failed to auto-start training:', startError);
          // Continue anyway - user can start manually from detail page
        }
      }

      // Redirect to the newly created training run
      router.push(`/monitor/${result.id}`);
    } catch (error) {
      console.error('Error creating training run:', error);
      alert('Failed to create training run. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Create Training Run
        </h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Configure and start a new training run
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Configuration</CardTitle>
            <CardDescription>
              Provide basic information about your training run
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="run_name">Run Name *</Label>
              <Input
                id="run_name"
                placeholder="e.g., phobert-finetune-001"
                {...register('run_name')}
              />
              {errors.run_name && (
                <p className="mt-1 text-sm text-red-600">{errors.run_name.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="model_name">Model Name *</Label>
              <Input
                id="model_name"
                placeholder="e.g., vinai/phobert-base"
                {...register('model_name')}
              />
              {errors.model_name && (
                <p className="mt-1 text-sm text-red-600">{errors.model_name.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="dataset_name">Dataset Name *</Label>
              <Input
                id="dataset_name"
                placeholder="e.g., squad_v2"
                {...register('dataset_name')}
              />
              {errors.dataset_name && (
                <p className="mt-1 text-sm text-red-600">{errors.dataset_name.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="output_dir">Output Directory</Label>
              <Input
                id="output_dir"
                placeholder="e.g., ./outputs/phobert-finetune"
                {...register('output_dir')}
              />
            </div>

            <div>
              <Label htmlFor="notes">Notes</Label>
              <textarea
                id="notes"
                rows={3}
                className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:border-gray-700 dark:bg-gray-950 dark:placeholder:text-gray-400"
                placeholder="Additional notes about this training run..."
                {...register('notes')}
              />
            </div>
          </CardContent>
        </Card>

        {/* Hyperparameters */}
        <Card>
          <CardHeader>
            <CardTitle>Hyperparameters</CardTitle>
            <CardDescription>
              Configure training hyperparameters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="learning_rate">Learning Rate *</Label>
                <Input
                  id="learning_rate"
                  type="number"
                  step="0.00001"
                  {...register('learning_rate')}
                />
                {errors.learning_rate && (
                  <p className="mt-1 text-sm text-red-600">{errors.learning_rate.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="batch_size">Batch Size *</Label>
                <Input
                  id="batch_size"
                  type="number"
                  {...register('batch_size')}
                />
                {errors.batch_size && (
                  <p className="mt-1 text-sm text-red-600">{errors.batch_size.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="num_epochs">Number of Epochs *</Label>
                <Input
                  id="num_epochs"
                  type="number"
                  {...register('num_epochs')}
                />
                {errors.num_epochs && (
                  <p className="mt-1 text-sm text-red-600">{errors.num_epochs.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="warmup_steps">Warmup Steps *</Label>
                <Input
                  id="warmup_steps"
                  type="number"
                  {...register('warmup_steps')}
                />
                {errors.warmup_steps && (
                  <p className="mt-1 text-sm text-red-600">{errors.warmup_steps.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="weight_decay">Weight Decay *</Label>
                <Input
                  id="weight_decay"
                  type="number"
                  step="0.01"
                  {...register('weight_decay')}
                />
                {errors.weight_decay && (
                  <p className="mt-1 text-sm text-red-600">{errors.weight_decay.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="save_steps">Save Steps *</Label>
                <Input
                  id="save_steps"
                  type="number"
                  {...register('save_steps')}
                />
              </div>

              <div>
                <Label htmlFor="eval_steps">Eval Steps *</Label>
                <Input
                  id="eval_steps"
                  type="number"
                  {...register('eval_steps')}
                />
              </div>

              <div>
                <Label htmlFor="logging_steps">Logging Steps *</Label>
                <Input
                  id="logging_steps"
                  type="number"
                  {...register('logging_steps')}
                />
              </div>
            </div>

            {/* Boolean Options */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="fp16"
                  className="h-4 w-4 rounded border-gray-300"
                  {...register('fp16')}
                />
                <Label htmlFor="fp16" className="cursor-pointer">
                  Enable FP16 (Mixed Precision)
                </Label>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="bf16"
                  className="h-4 w-4 rounded border-gray-300"
                  {...register('bf16')}
                />
                <Label htmlFor="bf16" className="cursor-pointer">
                  Enable BF16 (Brain Float 16)
                </Label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Auto-start Option */}
        <Card>
          <CardHeader>
            <CardTitle>Training Options</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="autoStart"
                className="h-4 w-4 rounded border-gray-300"
                checked={autoStart}
                onChange={(e) => setAutoStart(e.target.checked)}
              />
              <Label htmlFor="autoStart" className="cursor-pointer">
                Start training automatically after creation
              </Label>
            </div>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              If unchecked, the training run will be created in PENDING status and you'll need to start it manually from the detail page.
            </p>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? (autoStart ? 'Creating & Starting...' : 'Creating...') : 'Create Training Run'}
          </Button>
        </div>
      </form>
    </div>
  );
}

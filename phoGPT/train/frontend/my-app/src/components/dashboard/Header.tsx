/**
 * Header component with theme toggle and user actions.
 */

'use client';

export default function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6 dark:border-gray-800 dark:bg-gray-900">
      {/* Page Title - Dynamic based on current page */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Training Dashboard
        </h2>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        {/* Refresh Indicator */}
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <span>Live</span>
        </div>

        {/* User Menu Placeholder */}
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-700" />
        </div>
      </div>
    </header>
  );
}

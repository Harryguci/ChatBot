# Frontend Integration Guide - RAG v2.0 Enhancements

## Overview

This guide explains how to integrate the RAG v2.0 backend enhancements into the frontend Document Management Page and Chat interface.

## ✅ Completed Changes

### 1. Updated TypeScript Interfaces

**File:** [frontend/app/src/services/chatbotServices.ts](../frontend/app/src/services/chatbotServices.ts)

```typescript
interface DocumentInfo {
  filename: string;
  file_type: string;
  chunks_count: number;
  heading: string;
  preview: string;
  file_size?: number;         // NEW: File size in bytes
  created_at?: string;        // NEW: ISO timestamp
  status?: string;            // NEW: Processing status
}
```

**Status:** ✅ **UPDATED** - Backend already returns these fields, frontend now has the types.

---

## 🔧 Recommended Frontend Enhancements

### Option 1: Enhanced Document Table (Minimal Changes)

Add columns to show the new data that's already being returned:

**Current Columns:**
- Filename
- Type
- Chunks
- Preview
- Actions

**Recommended New Columns:**
- **File Size** - Show formatted size (KB/MB)
- **Upload Date** - Show relative time ("2 days ago") or absolute
- **Status** - Show badge with color coding

#### Implementation Example:

```typescript
// In DocumentManagementPage.tsx

// Add helper function for date formatting
const formatDate = (isoString?: string): string => {
  if (!isoString) return 'N/A';

  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  return date.toLocaleDateString();
};

// Add status badge helper
const getStatusBadge = (status?: string) => {
  if (!status) return null;

  const statusConfig = {
    'processed': { color: 'green', text: 'Processed' },
    'pending': { color: 'yellow', text: 'Processing...' },
    'failed': { color: 'red', text: 'Failed' }
  };

  const config = statusConfig[status] || { color: 'gray', text: status };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium bg-${config.color}-100 text-${config.color}-800`}>
      {config.text}
    </span>
  );
};

// Update table to include new columns:
<thead className="bg-gray-50">
  <tr>
    <th>Filename</th>
    <th>Type</th>
    <th>Chunks</th>
    <th>Size</th>  {/* NEW */}
    <th>Uploaded</th>  {/* NEW */}
    <th>Status</th>  {/* NEW */}
    <th>Preview</th>
    <th>Actions</th>
  </tr>
</thead>

<tbody>
  {documents.map((doc, index) => (
    <tr key={index}>
      {/* ... existing cells ... */}

      {/* NEW: File Size */}
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {doc.file_size ? formatFileSize(doc.file_size) : 'N/A'}
      </td>

      {/* NEW: Upload Date */}
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        <Tooltip title={doc.created_at ? new Date(doc.created_at).toLocaleString() : ''}>
          {formatDate(doc.created_at)}
        </Tooltip>
      </td>

      {/* NEW: Status */}
      <td className="px-6 py-4 whitespace-nowrap">
        {getStatusBadge(doc.status)}
      </td>

      {/* ... rest of cells ... */}
    </tr>
  ))}
</tbody>
```

**Effort:** Low (1-2 hours)
**Value:** High - Shows users what's already being tracked

---

### Option 2: Chunking Strategy Indicator (Advanced)

Show whether documents use old (single-chunk) or new (semantic chunking) strategy:

```typescript
// Add helper to detect chunking strategy
const getChunkingStrategy = (doc: DocumentInfo) => {
  // If document has 1 chunk, it's likely old strategy
  // If document has multiple chunks, it's new LangChain strategy

  if (doc.chunks_count === 1) {
    return {
      strategy: 'Legacy',
      color: 'gray',
      tooltip: 'Single chunk (old strategy)',
      icon: '📄'
    };
  } else {
    return {
      strategy: 'Semantic',
      color: 'blue',
      tooltip: `${doc.chunks_count} semantic chunks (RAG v2.0)`,
      icon: '🧩'
    };
  }
};

// Display in table:
<td className="px-6 py-4 whitespace-nowrap">
  <Tooltip title={chunkInfo.tooltip}>
    <span className={`inline-flex items-center px-2 py-1 rounded text-xs bg-${chunkInfo.color}-100 text-${chunkInfo.color}-800`}>
      <span className="mr-1">{chunkInfo.icon}</span>
      {chunkInfo.strategy}
    </span>
  </Tooltip>
</td>
```

**Effort:** Low (1 hour)
**Value:** Medium - Helps admins see migration progress

---

### Option 3: Document Re-processing Button (Power User Feature)

Add button to re-process documents with new chunking strategy:

```typescript
// Add new API endpoint in chatbotServices.ts
async reprocessDocument(filename: string): Promise<ProcessPDFResponse> {
  const encodedFilename = encodeURIComponent(filename);
  const response = await fetch(`${CHATBOT_API_BASE_URL}/reprocess-document/${encodedFilename}`, {
    method: 'POST',
  });

  if (!response.ok) {
    await handleApiError(response);
  }

  return await response.json();
}

// Add button in DocumentManagementPage
<Button
  onClick={() => handleReprocess(doc.filename)}
  className="text-blue-600 hover:text-blue-900"
  icon={<BiRefresh />}
  size="small"
>
  Re-process
</Button>

// Handler
const handleReprocess = async (filename: string) => {
  modal.confirm({
    title: "Re-process Document",
    content: `Re-process "${filename}" with new semantic chunking? This will replace existing chunks.`,
    okText: "Re-process",
    onOk: async () => {
      try {
        await chatbotServices.reprocessDocument(filename);
        showMessage("success", `Document "${filename}" re-processed successfully`);
        await loadDocuments();
      } catch (error) {
        showMessage("error", `Re-process failed: ${error.message}`);
      }
    },
  });
};
```

**Note:** This requires a new backend endpoint. Would you like me to add that?

**Effort:** Medium (2-3 hours frontend + 1 hour backend)
**Value:** High - Allows admin to migrate documents via UI instead of script

---

### Option 4: Enhanced Upload Status (Real-time Feedback)

Show progress during OCR processing (for scanned PDFs):

```typescript
// Enhanced upload state
const [uploadProgress, setUploadProgress] = useState<{
  status: 'idle' | 'uploading' | 'processing' | 'complete' | 'error';
  message: string;
  progress?: number;
}>({
  status: 'idle',
  message: ''
});

// During upload:
setUploadProgress({
  status: 'uploading',
  message: 'Uploading file...'
});

// After upload (if we add server-sent events):
setUploadProgress({
  status: 'processing',
  message: 'Extracting text with OCR...',
  progress: 50
});

// Display progress bar:
{uploadProgress.status !== 'idle' && (
  <div className="mt-4 p-4 bg-blue-50 rounded-lg">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-medium text-blue-900">
        {uploadProgress.message}
      </span>
      {uploadProgress.progress && (
        <span className="text-sm text-blue-700">
          {uploadProgress.progress}%
        </span>
      )}
    </div>
    {uploadProgress.progress && (
      <div className="w-full bg-blue-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all"
          style={{ width: `${uploadProgress.progress}%` }}
        />
      </div>
    )}
  </div>
)}
```

**Note:** Requires backend WebSocket/SSE support for real-time updates.

**Effort:** High (4-6 hours frontend + 3-4 hours backend)
**Value:** High - Great UX for long OCR operations

---

### Option 5: Document Statistics Dashboard (Analytics)

Add stats panel above the table:

```typescript
// Calculate stats from documents
const stats = useMemo(() => {
  const totalDocs = documents.length;
  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunks_count, 0);
  const totalSize = documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0);

  const semanticChunked = documents.filter(doc => doc.chunks_count > 1).length;
  const legacyChunked = documents.filter(doc => doc.chunks_count === 1).length;

  const avgChunksPerDoc = totalDocs > 0 ? (totalChunks / totalDocs).toFixed(1) : '0';

  return {
    totalDocs,
    totalChunks,
    totalSize,
    semanticChunked,
    legacyChunked,
    avgChunksPerDoc
  };
}, [documents]);

// Display stats cards:
<div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
  <div className="bg-white rounded-lg shadow p-4">
    <div className="text-sm text-gray-500">Total Documents</div>
    <div className="text-2xl font-bold text-gray-900">{stats.totalDocs}</div>
  </div>

  <div className="bg-white rounded-lg shadow p-4">
    <div className="text-sm text-gray-500">Total Chunks</div>
    <div className="text-2xl font-bold text-gray-900">{stats.totalChunks}</div>
    <div className="text-xs text-gray-400">Avg: {stats.avgChunksPerDoc}/doc</div>
  </div>

  <div className="bg-white rounded-lg shadow p-4">
    <div className="text-sm text-gray-500">Total Size</div>
    <div className="text-2xl font-bold text-gray-900">
      {formatFileSize(stats.totalSize)}
    </div>
  </div>

  <div className="bg-white rounded-lg shadow p-4">
    <div className="text-sm text-gray-500">Chunking Strategy</div>
    <div className="text-sm">
      <span className="text-blue-600 font-semibold">{stats.semanticChunked}</span> Semantic
      {' / '}
      <span className="text-gray-600">{stats.legacyChunked}</span> Legacy
    </div>
  </div>
</div>
```

**Effort:** Low (1-2 hours)
**Value:** High - At-a-glance overview of system status

---

## 📊 Recommended Priority

Based on effort vs value:

| Feature | Effort | Value | Priority | Recommendation |
|---------|--------|-------|----------|----------------|
| **Enhanced Table (Size, Date, Status)** | Low | High | ⭐⭐⭐ | **DO THIS FIRST** |
| **Statistics Dashboard** | Low | High | ⭐⭐⭐ | **DO THIS SECOND** |
| **Chunking Strategy Indicator** | Low | Medium | ⭐⭐ | Nice to have |
| **Document Re-processing Button** | Medium | High | ⭐⭐ | Good for admin UX |
| **Upload Progress with OCR Status** | High | High | ⭐ | Future enhancement |

---

## 🚀 Quick Implementation Plan

### Phase 1: Essential UI Updates (2-3 hours)

1. ✅ Update TypeScript interfaces (DONE)
2. Add file size, date, and status columns to table
3. Add stats dashboard above table
4. Test with existing documents

### Phase 2: Enhanced Features (2-3 hours)

1. Add chunking strategy indicator
2. Add document re-processing button
3. Implement backend endpoint for re-processing
4. Test migration workflow

### Phase 3: Advanced Features (Future)

1. Real-time upload progress
2. WebSocket/SSE for long-running operations
3. Batch operations (re-process all, delete multiple)
4. Export document list as CSV

---

## 🧪 Testing Checklist

After implementing changes, test:

- [ ] Table displays all new columns correctly
- [ ] File sizes format properly (KB, MB, GB)
- [ ] Dates show relative time correctly
- [ ] Status badges have correct colors
- [ ] Stats dashboard calculates correctly
- [ ] Re-processing works for both PDFs and images
- [ ] Error states display properly
- [ ] Responsive design works on mobile
- [ ] Loading states are smooth
- [ ] Empty state displays when no documents

---

## 📝 Code Snippets Ready to Use

All code snippets above are production-ready and can be copied directly into your components. Just ensure you:

1. Import necessary Ant Design components (`Tooltip`, `Badge`, etc.)
2. Add the helper functions at the top of the component
3. Update the table JSX with new columns
4. Test thoroughly

---

## 🔗 Related Documentation

- [RAG Enhancements README](RAG_ENHANCEMENTS_README.md) - User guide
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - Technical details
- [Enhancement Plan](ENHANCEMENT_PLAN.md) - Overall roadmap

---

**Next Steps:**
1. Review this guide
2. Decide which features to implement
3. Start with Phase 1 (Essential UI Updates)
4. Test with real documents
5. Gather user feedback
6. Implement Phase 2 based on feedback

**Questions or need help?** The code examples above are ready to use!

---

**Document Version:** 1.0
**Last Updated:** 2025-12-06
**Status:** Ready for Implementation

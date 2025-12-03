"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, FileText, X } from "lucide-react";
import { Textarea } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const EXAMPLE_QUERIES = [
  {
    label: "CRPS Treatment",
    query:
      "62-year-old male with cold-type CRPS of the right hand, failed gabapentin and physical therapy. What treatment approach would you recommend?",
  },
  {
    label: "Resistant HTN",
    query:
      "55-year-old female with resistant hypertension on 4 medications, recent renal artery stenosis ruled out. Next steps?",
  },
  {
    label: "Unusual Rash",
    query:
      "35-year-old with recurrent erythematous patches on trunk, steroid-responsive but frequently recurring. Biopsy shows perivascular lymphocytic infiltrate.",
  },
];

interface QueryInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export function QueryInput({ onSubmit, disabled, loading }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const [showExamples, setShowExamples] = useState(false);

  const handleSubmit = () => {
    if (query.trim() && !disabled && !loading) {
      onSubmit(query.trim());
    }
  };

  const handleExample = (example: string) => {
    setQuery(example);
    setShowExamples(false);
  };

  return (
    <div className="space-y-4">
      {/* Main input */}
      <div className="relative">
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Describe the clinical scenario you'd like the conference to deliberate on..."
          disabled={disabled || loading}
          className="min-h-[140px] pr-12 text-base"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.metaKey) {
              handleSubmit();
            }
          }}
        />

        {/* Character count */}
        <div className="absolute bottom-3 left-4 text-xs text-slate-500 font-mono">
          {query.length} chars
        </div>

        {/* Submit button - floating */}
        <Button
          onClick={handleSubmit}
          disabled={!query.trim() || disabled || loading}
          loading={loading}
          className="absolute bottom-3 right-3"
          size="sm"
        >
          <Send className="w-4 h-4" />
          <span className="sr-only">Start Conference</span>
        </Button>
      </div>

      {/* Examples toggle */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowExamples(!showExamples)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Sparkles className="w-4 h-4" />
          <span>{showExamples ? "Hide examples" : "Try an example"}</span>
        </button>

        <div className="text-xs text-slate-500">
          <kbd className="px-1.5 py-0.5 rounded bg-void-300 border border-white/10">
            ⌘
          </kbd>{" "}
          +{" "}
          <kbd className="px-1.5 py-0.5 rounded bg-void-300 border border-white/10">
            Enter
          </kbd>{" "}
          to submit
        </div>
      </div>

      {/* Example queries */}
      <AnimatePresence>
        {showExamples && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="grid gap-2 pt-2">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  key={example.label}
                  onClick={() => handleExample(example.query)}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg text-left transition-all",
                    "bg-void-200/30 border border-white/5",
                    "hover:bg-void-200/50 hover:border-white/10"
                  )}
                >
                  <FileText className="w-4 h-4 text-accent-primary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-slate-200">
                      {example.label}
                    </p>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                      {example.query}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// File upload component for Librarian
interface FileUploadProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

export function FileUpload({ files, onFilesChange, disabled }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (disabled) return;

    const droppedFiles = Array.from(e.dataTransfer.files);
    onFilesChange([...files, ...droppedFiles]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      onFilesChange([...files, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "relative flex flex-col items-center justify-center p-6 rounded-lg border-2 border-dashed transition-all cursor-pointer",
          isDragging
            ? "border-accent-primary bg-accent-primary/5"
            : "border-white/10 hover:border-white/20 bg-void-200/20",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <input
          type="file"
          multiple
          onChange={handleFileInput}
          disabled={disabled}
          className="absolute inset-0 opacity-0 cursor-pointer"
          accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.md"
        />
        <FileText className="w-8 h-8 text-slate-500 mb-2" />
        <p className="text-sm text-slate-400">
          Drop files here or <span className="text-accent-primary">browse</span>
        </p>
        <p className="text-xs text-slate-500 mt-1">
          PDF, images, or text files
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between p-2 rounded-lg bg-void-200/30 border border-white/5"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                <span className="text-sm text-slate-300 truncate">
                  {file.name}
                </span>
                <span className="text-xs text-slate-500">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
              <button
                onClick={() => removeFile(index)}
                className="p-1 hover:bg-white/5 rounded"
              >
                <X className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


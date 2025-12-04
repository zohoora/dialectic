"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { User, ChevronDown, ChevronUp, Plus, X } from "lucide-react";

import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PatientContext } from "@/lib/api";

interface PatientContextFormProps {
  value: PatientContext;
  onChange: (context: PatientContext) => void;
  disabled?: boolean;
}

export function PatientContextForm({
  value,
  onChange,
  disabled = false,
}: PatientContextFormProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [newComorbidity, setNewComorbidity] = useState("");
  const [newMedication, setNewMedication] = useState("");
  const [newAllergy, setNewAllergy] = useState("");
  const [newFailedTreatment, setNewFailedTreatment] = useState("");
  const [newConstraint, setNewConstraint] = useState("");

  const hasContent =
    value.age ||
    value.sex ||
    (value.comorbidities?.length ?? 0) > 0 ||
    (value.current_medications?.length ?? 0) > 0 ||
    (value.allergies?.length ?? 0) > 0 ||
    (value.failed_treatments?.length ?? 0) > 0 ||
    value.relevant_history ||
    (value.constraints?.length ?? 0) > 0;

  const addToList = (
    field: keyof PatientContext,
    newValue: string,
    setNewValue: (v: string) => void
  ) => {
    if (!newValue.trim()) return;
    const currentList = (value[field] as string[]) || [];
    onChange({
      ...value,
      [field]: [...currentList, newValue.trim()],
    });
    setNewValue("");
  };

  const removeFromList = (field: keyof PatientContext, index: number) => {
    const currentList = (value[field] as string[]) || [];
    onChange({
      ...value,
      [field]: currentList.filter((_, i) => i !== index),
    });
  };

  return (
    <Card className="bg-slate-800/30 border-slate-700/50">
      <CardHeader
        className="py-3 px-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
        onClick={() => !disabled && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <User className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <h3 className="font-medium text-slate-200">Patient Context</h3>
              <p className="text-xs text-slate-400">
                {hasContent
                  ? "Provides routing context for agent selection"
                  : "Optional - helps route to the right agents"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {hasContent && (
              <Badge className="bg-cyan-500/20 text-cyan-300">Configured</Badge>
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
      </CardHeader>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <CardContent className="pt-0 space-y-4">
              {/* Demographics */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Age</label>
                  <Input
                    type="number"
                    min={0}
                    max={150}
                    value={value.age || ""}
                    onChange={(e) =>
                      onChange({
                        ...value,
                        age: e.target.value ? parseInt(e.target.value) : undefined,
                      })
                    }
                    placeholder="e.g., 45"
                    disabled={disabled}
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Sex</label>
                  <select
                    className={cn(
                      "w-full h-9 px-3 rounded-md border bg-slate-900 text-slate-200",
                      "border-slate-700 focus:border-cyan-500/50 focus:outline-none",
                      disabled && "opacity-50 cursor-not-allowed"
                    )}
                    value={value.sex || ""}
                    onChange={(e) =>
                      onChange({
                        ...value,
                        sex: e.target.value as "male" | "female" | "other" | undefined,
                      })
                    }
                    disabled={disabled}
                  >
                    <option value="">Not specified</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              {/* Comorbidities */}
              <ListInput
                label="Comorbidities"
                items={value.comorbidities || []}
                newValue={newComorbidity}
                setNewValue={setNewComorbidity}
                onAdd={() =>
                  addToList("comorbidities", newComorbidity, setNewComorbidity)
                }
                onRemove={(idx) => removeFromList("comorbidities", idx)}
                placeholder="e.g., Type 2 Diabetes"
                disabled={disabled}
              />

              {/* Current Medications */}
              <ListInput
                label="Current Medications"
                items={value.current_medications || []}
                newValue={newMedication}
                setNewValue={setNewMedication}
                onAdd={() =>
                  addToList("current_medications", newMedication, setNewMedication)
                }
                onRemove={(idx) => removeFromList("current_medications", idx)}
                placeholder="e.g., Metformin 1000mg"
                disabled={disabled}
              />

              {/* Allergies */}
              <ListInput
                label="Allergies"
                items={value.allergies || []}
                newValue={newAllergy}
                setNewValue={setNewAllergy}
                onAdd={() => addToList("allergies", newAllergy, setNewAllergy)}
                onRemove={(idx) => removeFromList("allergies", idx)}
                placeholder="e.g., Penicillin"
                disabled={disabled}
                badgeColor="red"
              />

              {/* Failed Treatments */}
              <ListInput
                label="Failed/Intolerant Treatments"
                items={value.failed_treatments || []}
                newValue={newFailedTreatment}
                setNewValue={setNewFailedTreatment}
                onAdd={() =>
                  addToList("failed_treatments", newFailedTreatment, setNewFailedTreatment)
                }
                onRemove={(idx) => removeFromList("failed_treatments", idx)}
                placeholder="e.g., Methotrexate (liver toxicity)"
                disabled={disabled}
                badgeColor="orange"
              />

              {/* Relevant History */}
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Relevant Medical History
                </label>
                <textarea
                  className={cn(
                    "w-full px-3 py-2 rounded-md border bg-slate-900 text-slate-200",
                    "border-slate-700 focus:border-cyan-500/50 focus:outline-none",
                    "resize-none h-20 text-sm",
                    disabled && "opacity-50 cursor-not-allowed"
                  )}
                  value={value.relevant_history || ""}
                  onChange={(e) =>
                    onChange({ ...value, relevant_history: e.target.value || undefined })
                  }
                  placeholder="Brief relevant medical history..."
                  disabled={disabled}
                />
              </div>

              {/* Constraints */}
              <ListInput
                label="Constraints & Preferences"
                items={value.constraints || []}
                newValue={newConstraint}
                setNewValue={setNewConstraint}
                onAdd={() => addToList("constraints", newConstraint, setNewConstraint)}
                onRemove={(idx) => removeFromList("constraints", idx)}
                placeholder="e.g., Cost sensitive, needle phobia"
                disabled={disabled}
                badgeColor="purple"
              />
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// =============================================================================
// LIST INPUT HELPER
// =============================================================================

interface ListInputProps {
  label: string;
  items: string[];
  newValue: string;
  setNewValue: (v: string) => void;
  onAdd: () => void;
  onRemove: (idx: number) => void;
  placeholder: string;
  disabled?: boolean;
  badgeColor?: "cyan" | "red" | "orange" | "purple";
}

function ListInput({
  label,
  items,
  newValue,
  setNewValue,
  onAdd,
  onRemove,
  placeholder,
  disabled,
  badgeColor = "cyan",
}: ListInputProps) {
  const colorMap = {
    cyan: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
    red: "bg-red-500/20 text-red-300 border-red-500/30",
    orange: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    purple: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  };

  return (
    <div>
      <label className="text-xs text-slate-400 mb-1 block">{label}</label>
      <div className="flex gap-2">
        <Input
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAdd();
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1"
        />
        <Button
          size="sm"
          variant="secondary"
          onClick={onAdd}
          disabled={disabled || !newValue.trim()}
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      {items.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {items.map((item, idx) => (
            <Badge
              key={idx}
              className={cn("pr-1 flex items-center gap-1", colorMap[badgeColor])}
            >
              {item}
              {!disabled && (
                <button
                  onClick={() => onRemove(idx)}
                  className="ml-1 hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}


import { Skeleton } from "@/components/ui/skeleton";

export function AnalysisLoading() {
  return (
    <div className="space-y-3 mt-4">
      <p className="text-sm text-muted-foreground animate-pulse">
        Analisando a base legislativa…
      </p>
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

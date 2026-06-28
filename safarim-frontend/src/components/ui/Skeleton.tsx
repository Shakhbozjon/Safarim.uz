import { clsx } from "clsx";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "shimmer-bg animate-shimmer rounded-lg",
        className
      )}
    />
  );
}

export function TripCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 space-y-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="flex items-center gap-4">
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-3 w-12" />
        </div>
        <Skeleton className="h-3 w-10" />
        <div className="flex-1 space-y-1.5 items-end flex flex-col">
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-3 w-12" />
        </div>
      </div>
      <div className="flex justify-between items-center pt-3 border-t border-gray-50">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-9 w-28 rounded-xl" />
      </div>
    </div>
  );
}

export function TripDetailSkeleton() {
  return (
    <div className="space-y-5 animate-fade-in">
      <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
        <Skeleton className="h-4 w-40" />
        <div className="space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-10 w-20" />
          </div>
          <Skeleton className="w-0.5 h-12 mx-3" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-32" />
          </div>
        </div>
      </div>
      <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
        <div className="flex items-center gap-4">
          <Skeleton className="w-14 h-14 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-36" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function BookingCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 space-y-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <div className="flex items-center gap-4">
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-3 w-10" />
        </div>
        <Skeleton className="h-px w-10" />
        <div className="flex-1 space-y-1.5 items-end flex flex-col">
          <Skeleton className="h-5 w-24" />
        </div>
      </div>
      <div className="flex gap-3 pt-3 border-t border-gray-50">
        <Skeleton className="h-9 flex-1 rounded-xl" />
        <Skeleton className="h-9 flex-1 rounded-xl" />
      </div>
    </div>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-4">
        <Skeleton className="w-16 h-16 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-28" />
        </div>
      </div>
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

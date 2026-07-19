"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Calendar, Clock, Users,
  Info, CheckCircle,
} from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import LocationPicker, { LocationValue, EMPTY_LOCATION } from "@/components/ui/LocationPicker";
import { clsx } from "clsx";
import api from "@/lib/api";
import { getApiError, isAuthenticated } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import BecomeDriver from "@/components/driver/BecomeDriver";
import { ProfileSkeleton } from "@/components/ui/Skeleton";

const schema = z.object({
  from_region_id:   z.number({ required_error: "Viloyat tanlang" }).positive("Viloyat tanlang"),
  from_district_id: z.number().nullable().optional(),
  to_region_id:     z.number({ required_error: "Viloyat tanlang" }).positive("Viloyat tanlang"),
  to_district_id:   z.number().nullable().optional(),
  departure_date: z.string().min(1, "Sana kiriting"),
  departure_time: z.string().min(1, "Vaqt kiriting"),
  total_seats:    z.number().min(1).max(8),
  price_per_seat: z.number().min(10_000, "Kamida 10,000 so'm"),
  payment_type:   z.enum(["cash", "click", "payme", "any"]),
  smoking_allowed: z.boolean(),
  pets_allowed:    z.boolean(),
  women_only:      z.boolean(),
  luggage_size:    z.enum(["small", "medium", "large"]),
  description:    z.string().max(500).optional(),
});

type FormData = z.infer<typeof schema>;

const STEPS = ["Marshrut", "Vaqt va joy", "Narx", "Qo'shimcha"];

export default function CreateTripPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  // Haydovchi bo'lmaganlar uchun ariza holati (gate uchun)
  const { data: driverStatus, isLoading: statusLoading } = useQuery<{
    status: "pending" | "approved" | "rejected";
  }>({
    queryKey: ["driver-status"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me/status");
      return data;
    },
    enabled: isAuthenticated() && !!user && !user.is_driver,
    retry: false, // 404 → ariza topshirilmagan, xato emas
  });

  const [step, setStep] = useState(1);
  const [apiError, setApiError] = useState("");
  const [fromLoc, setFromLoc] = useState<LocationValue>(EMPTY_LOCATION);
  const [toLoc, setToLoc]     = useState<LocationValue>(EMPTY_LOCATION);

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      total_seats:    3,
      price_per_seat: 45_000,
      payment_type:   "any",
      smoking_allowed: false,
      pets_allowed:    false,
      women_only:      false,
      luggage_size:    "medium",
    },
  });

  const seats = watch("total_seats");
  const price = watch("price_per_seat");
  const depDate = watch("departure_date");
  const depTime = watch("departure_time");

  const fromName = fromLoc.districtName
    ? `${fromLoc.regionName}, ${fromLoc.districtName}`
    : fromLoc.regionName;
  const toName = toLoc.districtName
    ? `${toLoc.regionName}, ${toLoc.districtName}`
    : toLoc.regionName;

  // LocationPicker o'zgarganda form qiymatlarini ham yangilash
  function handleFromChange(val: LocationValue) {
    setFromLoc(val);
    setValue("from_region_id",   val.regionId   ?? 0);
    setValue("from_district_id", val.districtId ?? null);
  }
  function handleToChange(val: LocationValue) {
    setToLoc(val);
    setValue("to_region_id",   val.regionId   ?? 0);
    setValue("to_district_id", val.districtId ?? null);
  }

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const { data: trip } = await api.post("/trips/", data);
      return trip;
    },
    onSuccess: (trip) => {
      router.push(`/trips/${trip.id}`);
    },
    onError: (err: any) => {
      setApiError(getApiError(err));
      setStep(1);
    },
  });

  async function onSubmit(data: FormData) {
    setApiError("");
    mutation.mutate(data);
  }

  // Qaysi maydon qaysi qadamda ekanini xaritalash
  const FIELD_STEP: Record<string, number> = {
    from_region_id: 1, from_district_id: 1, to_region_id: 1, to_district_id: 1,
    departure_date: 2, departure_time: 2, total_seats: 2,
    price_per_seat: 3, payment_type: 3,
    smoking_allowed: 4, pets_allowed: 4, women_only: 4, luggage_size: 4, description: 4,
  };

  // Zod validatsiya muvaffaqiyatsiz bo'lsa — xatoni ko'rsatib, tegishli qadamga o'tish
  function onInvalid(errs: Record<string, any>) {
    const firstKey = Object.keys(errs)[0];
    const msg = errs[firstKey]?.message || "Ba'zi maydonlar to'ldirilmagan. Iltimos tekshiring.";
    setApiError(msg);
    const targetStep = FIELD_STEP[firstKey];
    if (targetStep) setStep(targetStep);
  }

  // ── Haydovchi darvozasi ──────────────────────────────────────────────────
  // Kirmagan yoki haydovchi bo'lmagan foydalanuvchi formani emas,
  // "Haydovchi bo'ling" onboarding ekranini ko'radi (403 o'rniga).
  const gateLoading =
    (isAuthenticated() && authLoading) ||
    (!!user && !user.is_driver && statusLoading);

  if (gateLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
        <ProfileSkeleton />
      </div>
    );
  }

  if (!user || !user.is_driver) {
    return <BecomeDriver user={user} applicationStatus={driverStatus?.status} />;
  }

  if (mutation.isSuccess) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="w-20 h-20 bg-green-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
          <CheckCircle size={40} className="text-green-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Safar e'lon qilindi!</h1>
        <p className="text-gray-500 mb-8">
          {fromName} → {toName} yo'nalishidagi safaringiz e'lon qilindi.
        </p>
        <div className="flex gap-3">
          <Button variant="outline" fullWidth onClick={() => router.push("/my-trips")}>
            Safarlarimni ko'rish
          </Button>
          <Button fullWidth onClick={() => router.push("/create-trip")}>
            Yana qo'shish
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-5">Safar e'lon qilish</h1>

        {/* Step indicators */}
        <div className="flex items-center gap-0">
          {STEPS.map((label, i) => {
            const n = i + 1;
            const done   = n < step;
            const active = n === step;
            return (
              <div key={n} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1">
                  <div className={clsx(
                    "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all",
                    done   ? "bg-green-500 text-white"   :
                    active ? "bg-primary-500 text-white" :
                    "bg-gray-100 text-gray-400"
                  )}>
                    {done ? "✓" : n}
                  </div>
                  <span className={clsx("text-xs hidden sm:block", active ? "text-primary-600 font-medium" : "text-gray-400")}>
                    {label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={clsx("flex-1 h-0.5 mb-5", done ? "bg-green-200" : "bg-gray-100")} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {apiError && (
        <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100 mb-4">
          {apiError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit, onInvalid)}>

        {/* ── STEP 1: Marshrut ── */}
        {step === 1 && (
          <div className="space-y-5 animate-fade-in">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
              <h2 className="text-base font-semibold text-gray-900 mb-1">Marshrut ma'lumotlari</h2>

              <div className="border border-gray-200 rounded-xl px-4 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20 transition-all">
                <p className="text-xs font-medium text-gray-400 pt-2.5">Qayerdan</p>
                <LocationPicker
                  value={fromLoc}
                  onChange={handleFromChange}
                  placeholder="Viloyat / shahar tanlang"
                  error={errors.from_region_id?.message}
                />
              </div>

              <div className="border border-gray-200 rounded-xl px-4 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20 transition-all">
                <p className="text-xs font-medium text-gray-400 pt-2.5">Qayerga</p>
                <LocationPicker
                  value={toLoc}
                  onChange={handleToChange}
                  placeholder="Viloyat / shahar tanlang"
                  error={errors.to_region_id?.message}
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                type="button"
                size="lg"
                disabled={!fromLoc.regionId || !toLoc.regionId}
                onClick={() => setStep(2)}
              >
                Keyingisi →
              </Button>
            </div>
          </div>
        )}

        {/* ── STEP 2: Vaqt va joy ── */}
        {step === 2 && (
          <div className="space-y-5 animate-fade-in">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
              <h2 className="text-base font-semibold text-gray-900 mb-1">Vaqt va o'rinlar</h2>

              <Input
                label="Sana"
                type="date"
                min={new Date().toISOString().split("T")[0]}
                prefix={<Calendar size={15} />}
                error={errors.departure_date?.message}
                {...register("departure_date")}
              />

              <Input
                label="Jo'nash vaqti"
                type="time"
                prefix={<Clock size={15} />}
                error={errors.departure_time?.message}
                {...register("departure_time")}
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Yo'lovchi o'rinlari: <span className="text-primary-600 font-bold">{seats}</span>
                </label>
                <input
                  type="range"
                  min={1} max={8} step={1}
                  value={seats}
                  onChange={(e) => setValue("total_seats", Number(e.target.value))}
                  className="w-full accent-primary-500"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>1</span><span>8</span>
                </div>
                <div className="flex gap-1 mt-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div
                      key={i}
                      onClick={() => setValue("total_seats", i + 1)}
                      className={clsx(
                        "flex-1 h-8 rounded-lg flex items-center justify-center cursor-pointer text-xs font-medium transition-all",
                        i < seats ? "bg-primary-100 text-primary-700" : "bg-gray-100 text-gray-400"
                      )}
                    >
                      <Users size={12} />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <Button type="button" variant="outline" size="lg" onClick={() => setStep(1)}>
                ← Orqaga
              </Button>
              <Button
                type="button"
                size="lg"
                className="flex-1"
                disabled={!depDate || !depTime}
                onClick={() => setStep(3)}
              >
                Keyingisi →
              </Button>
            </div>
          </div>
        )}

        {/* ── STEP 3: Narx ── */}
        {step === 3 && (
          <div className="space-y-5 animate-fade-in">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
              <h2 className="text-base font-semibold text-gray-900 mb-1">Narxni belgilang</h2>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Bir joy narxi:{" "}
                  <span className="text-primary-600 font-bold tabular-nums">
                    {new Intl.NumberFormat("uz-UZ").format(price)} so'm
                  </span>
                </label>
                <input
                  type="range"
                  min={10_000} max={300_000} step={5_000}
                  value={price}
                  onChange={(e) => setValue("price_per_seat", Number(e.target.value))}
                  className="w-full accent-primary-500"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>10,000</span><span>300,000 so'm</span>
                </div>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Bir joy narxi</span>
                  <span className="font-medium">{new Intl.NumberFormat("uz-UZ").format(price)} so'm</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">
                    Platforma komissiyasi ({price > 200_000 ? "5" : "2"}%)
                  </span>
                  <span className="text-gray-500">
                    −{new Intl.NumberFormat("uz-UZ").format(Math.round(price * (price > 200_000 ? 0.05 : 0.02)))} so'm
                  </span>
                </div>
                <div className="flex justify-between text-sm font-semibold border-t border-gray-200 pt-2">
                  <span className="text-gray-700">Siz olasiz</span>
                  <span className="text-green-600">
                    {new Intl.NumberFormat("uz-UZ").format(Math.round(price * (price > 200_000 ? 0.95 : 0.98)))} so'm
                  </span>
                </div>
              </div>

              {/* To'lov turi */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">To'lov usuli</label>
                <div className="grid grid-cols-2 gap-2">
                  {([
                    { value: "any",   label: "Har qanday" },
                    { value: "cash",  label: "Naqd pul" },
                    { value: "click", label: "Click" },
                    { value: "payme", label: "Payme" },
                  ] as const).map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setValue("payment_type", value)}
                      className={clsx(
                        "py-2.5 rounded-xl text-sm font-medium border transition-all",
                        watch("payment_type") === value
                          ? "border-primary-500 bg-primary-50 text-primary-700"
                          : "border-gray-200 text-gray-600"
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-start gap-2.5 text-xs text-gray-500 bg-blue-50 rounded-xl p-3">
                <Info size={13} className="text-blue-400 mt-0.5 shrink-0" />
                Yo'lovchilarni jalb qilish uchun bozor narxiga yaqin belgilang.
              </div>
            </div>

            <div className="flex gap-3">
              <Button type="button" variant="outline" size="lg" onClick={() => setStep(2)}>
                ← Orqaga
              </Button>
              <Button type="button" size="lg" className="flex-1" onClick={() => setStep(4)}>
                Keyingisi →
              </Button>
            </div>
          </div>
        )}

        {/* ── STEP 4: Qo'shimcha ── */}
        {step === 4 && (
          <div className="space-y-5 animate-fade-in">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
              <h2 className="text-base font-semibold text-gray-900 mb-1">Qo'shimcha ma'lumotlar</h2>

              {/* Shartlar */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Shartlar</label>
                <div className="grid grid-cols-3 gap-2">
                  {([
                    { key: "smoking_allowed" as const, icon: "🚬", label: "Chekish mumkin" },
                    { key: "pets_allowed"    as const, icon: "🐾", label: "Hayvon mumkin" },
                    { key: "women_only"      as const, icon: "👩", label: "Faqat ayollar" },
                  ]).map(({ key, icon, label }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setValue(key, !watch(key))}
                      className={clsx(
                        "flex flex-col items-center gap-2 p-3.5 rounded-xl border text-xs font-medium transition-all",
                        watch(key)
                          ? "border-primary-500 bg-primary-50 text-primary-700"
                          : "border-gray-100 bg-gray-50 text-gray-600 hover:border-gray-200"
                      )}
                    >
                      <span className="text-xl">{icon}</span>
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Yukxalta hajmi */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Yukxalta hajmi</label>
                <div className="grid grid-cols-3 gap-2">
                  {([
                    { value: "small",  label: "Kichik", icon: "🎒" },
                    { value: "medium", label: "O'rtacha", icon: "🧳" },
                    { value: "large",  label: "Katta", icon: "📦" },
                  ] as const).map(({ value, label, icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setValue("luggage_size", value)}
                      className={clsx(
                        "flex flex-col items-center gap-2 p-3.5 rounded-xl border text-xs font-medium transition-all",
                        watch("luggage_size") === value
                          ? "border-primary-500 bg-primary-50 text-primary-700"
                          : "border-gray-100 bg-gray-50 text-gray-600"
                      )}
                    >
                      <span className="text-xl">{icon}</span>
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Izoh */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Qo'shimcha izoh
                  <span className="text-gray-400 font-normal ml-1">(ixtiyoriy)</span>
                </label>
                <textarea
                  {...register("description")}
                  rows={3}
                  placeholder="Masalan: Jizzax orqali ketamiz. Sigaret chekish ta'qiqlangan."
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
                />
              </div>

              {/* Xulosa */}
              <div className="bg-gray-50 rounded-xl p-4 space-y-2 border border-gray-100">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Xulosa</p>
                {[
                  { label: "Marshrut",  value: `${fromName || "—"} → ${toName || "—"}` },
                  { label: "O'rinlar",  value: `${seats} ta yo'lovchi` },
                  { label: "Narx",      value: `${new Intl.NumberFormat("uz-UZ").format(price)} so'm/joy` },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between text-sm">
                    <span className="text-gray-500">{label}</span>
                    <span className="font-medium text-gray-900">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <Button type="button" variant="outline" size="lg" onClick={() => setStep(3)}>
                ← Orqaga
              </Button>
              <Button
                type="submit"
                size="lg"
                className="flex-1"
                loading={mutation.isPending}
              >
                E'lon qilish
              </Button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}

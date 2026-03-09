import { SupportForm } from "@/components/SupportForm";

export default function Home() {
  return (
    <div className="flex min-h-screen items-start justify-center bg-gray-50 px-4 py-12">
      <main className="w-full max-w-2xl">
        <h1 className="mb-6 text-2xl font-semibold text-gray-900">
          Customer Support
        </h1>
        <SupportForm />
      </main>
    </div>
  );
}

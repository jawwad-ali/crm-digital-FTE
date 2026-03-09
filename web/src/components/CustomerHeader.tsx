"use client";

interface CustomerHeaderProps {
  name: string;
  email: string;
}

export function CustomerHeader({ name, email }: CustomerHeaderProps) {
  return (
    <div className="rounded-lg bg-gray-100 px-3 py-2 sm:px-4 sm:py-2.5 text-sm text-gray-700" aria-label={`Logged in as ${name}`}>
      <span className="font-medium">{name}</span>{" "}
      <span className="text-gray-500 break-all">({email})</span>
    </div>
  );
}

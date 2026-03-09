"use client";

interface CustomerHeaderProps {
  name: string;
  email: string;
}

export function CustomerHeader({ name, email }: CustomerHeaderProps) {
  return (
    <div className="rounded-lg bg-gray-100 px-4 py-2.5 text-sm text-gray-700">
      <span className="font-medium">{name}</span>{" "}
      <span className="text-gray-500">({email})</span>
    </div>
  );
}

"use client";

import React from "react";
import Image from "next/image";

interface AiraLogoProps {
  className?: string;
  width?: number;
  height?: number;
}

export default function AiraLogo({
  className = "h-6 w-auto",
  width = 110,
  height = 38,
}: AiraLogoProps) {
  return (
    <Image
      src="/aira-logo.svg"
      alt="Aira Logo"
      width={width}
      height={height}
      className={className}
      priority
    />
  );
}

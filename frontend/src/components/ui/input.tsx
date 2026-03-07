import * as React from 'react';
import { cn } from '@/utils/cn';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-9 w-full rounded-lg border border-[#e9e9e8] bg-white px-3 py-2 text-sm text-[#37352f] shadow-sm transition-colors',
          'placeholder:text-[#b4b4b3]',
          'focus:outline-none focus:border-[#2383e2] focus:ring-2 focus:ring-[#2383e2]/20',
          'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-[#f9f9f8]',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };

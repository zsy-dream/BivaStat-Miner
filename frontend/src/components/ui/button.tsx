/* eslint-disable react-refresh/only-export-components */
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default:
          'bg-[#2383e2] text-white shadow-sm hover:bg-[#0070d2] active:scale-[0.98]',
        destructive:
          'bg-red-500 text-white shadow-sm hover:bg-red-600 active:scale-[0.98]',
        outline:
          'border border-[#e9e9e8] bg-white text-[#37352f] shadow-sm hover:bg-[#f9f9f8] hover:border-[#d3d3d3] active:scale-[0.98]',
        secondary:
          'bg-[#efefee] text-[#37352f] shadow-sm hover:bg-[#e5e5e4] active:scale-[0.98]',
        ghost:
          'text-[#37352f] hover:bg-[#efefee] hover:text-[#37352f] active:scale-[0.98]',
        link:
          'text-[#2383e2] underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 py-1.5 text-xs',
        lg: 'h-11 rounded-xl px-8 text-base',
        xl: 'h-14 rounded-2xl px-10 text-base font-bold',
        icon: 'h-9 w-9',
        'icon-sm': 'h-8 w-8 rounded-md',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };

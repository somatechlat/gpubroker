import React from 'react'
import { colors } from './DesignSystem'

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'success'
}

/**
 * Simple reusable button component that uses the design system colour palette.
 * Uses Tailwind utility classes for layout and hover/focus states.
 */
export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  className = '',
  children,
  ...rest
}) => {
  const base = 'px-4 py-2 rounded font-medium focus:outline-none transition-colors'
  const variantClasses: Record<string, string> = {
    primary: `bg-${colors.primary} text-white hover:bg-${colors.primaryLight}`,
    secondary: `bg-${colors.muted} text-white hover:bg-${colors.muted}`,
    danger: `bg-${colors.danger} text-white hover:bg-${colors.danger}`,
    success: `bg-${colors.success} text-white hover:bg-${colors.success}`,
  }

  // Tailwind does not support dynamic class names, so we fallback to inline style for colours.
  const styleMap: Record<string, React.CSSProperties> = {
    primary: { backgroundColor: colors.primary, color: '#fff' },
    secondary: { backgroundColor: colors.muted, color: '#fff' },
    danger: { backgroundColor: colors.danger, color: '#fff' },
    success: { backgroundColor: colors.success, color: '#fff' },
  }

  return (
    <button
      className={`${base} ${className}`}
      style={styleMap[variant]}
      {...rest}
    >
      {children}
    </button>
  )
}
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
}

export function Button({ variant = 'primary', className = '', ...props }: ButtonProps) {
  const base = 'py-2 px-4 rounded-md font-medium transition-colors duration-150'
  const variants: Record<string, string> = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700',
    secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
    ghost: 'bg-transparent text-gray-700 hover:bg-gray-100'
  }
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />
}

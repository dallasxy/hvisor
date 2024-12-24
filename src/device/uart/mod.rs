#[cfg(all(feature = "platform_qemu", target_arch = "aarch64"))]
mod pl011;

#[cfg(all(feature = "platform_qemu", target_arch = "aarch64"))]
pub use pl011::{console_getchar, console_putchar};

#[cfg(all(feature = "platform_imx8mp", target_arch = "aarch64"))]
mod imx_uart;

#[cfg(all(feature = "platform_imx8mp", target_arch = "aarch64"))]
pub use imx_uart::{console_getchar, console_putchar};

#[cfg(target_arch = "riscv64")]
pub use crate::arch::riscv64::sbi::{console_getchar, console_putchar};

#[cfg(target_arch = "loongarch64")]
mod ns16440a;

#[cfg(target_arch = "loongarch64")]
pub use ns16440a::{console_getchar, console_putchar};

// #[cfg(all(feature = "platform_rk3568", target_arch = "aarch64"))]
// mod rk3568_uart;

// #[cfg(all(feature = "platform_rk3568", target_arch = "aarch64"))]
// pub use rk3568_uart::{console_getchar, console_putchar};

#[cfg(all(feature = "platform_rk3568", target_arch = "aarch64"))]
pub mod uart_16550;

#[cfg(all(feature = "platform_rk3568", target_arch = "aarch64"))]
pub use uart_16550::{console_getchar, console_putchar};
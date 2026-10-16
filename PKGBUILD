
# Maintainer: Ticklebutt

pkgname=miyufetch-git
pkgver=0.1.r0.g0000000
pkgrel=1
pkgdesc="Python system information fetch utility with optional artwork"
arch=('any')
url="https://github.com/YOUR_USERNAME/miyufetch"
license=('MIT')
depends=('python')
optdepends=(
  'kitty: native terminal image display'
  'chafa: image rendering in other terminals'
  'pciutils: detailed GPU identification'
)
makedepends=('git')
source=("miyufetch::git+https://github.com/YOUR_USERNAME/miyufetch.git")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/miyufetch"
  printf '0.1.r%s.g%s' \
    "$(git rev-list --count HEAD)" \
    "$(git rev-parse --short HEAD)"
}

package() {
  cd "$srcdir/miyufetch"

  install -Dm755 miyufetch.py \
    "$pkgdir/usr/bin/miyufetch"

  install -Dm644 README.md \
    "$pkgdir/usr/share/doc/miyufetch/README.md"

  install -Dm644 LICENSE \
    "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

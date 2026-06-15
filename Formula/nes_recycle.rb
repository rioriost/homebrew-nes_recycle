class NesRecycle < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for previewing and submitting the Nespresso recycling pickup form over HTTP"
  homepage "https://github.com/rioriost/nes_recycle"
  url "https://github.com/rioriost/nes_recycle/releases/download/0.0.6/nes_recycle-0.0.6.tar.gz"
  sha256 "152252b71042389cb2d80ada6c7609c24112dec1b59ee16b2fe8643185ad7f6a"
  license "MIT"

  depends_on "python@3.14"

  def install
    if OS.mac?
      ENV.append "LDFLAGS", "-Wl,-headerpad_max_install_names"
      ENV.append "RUSTFLAGS", "-C link-arg=-Wl,-headerpad_max_install_names"
    end
    cd "." do
      virtualenv_install_with_resources
    end
  end

  test do
    system "#{bin}/nes_recycle", "--help"
  end
end

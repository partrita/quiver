use clap::Parser;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::Path;

/// Combines multiple PDB files into a Quiver-compatible stream.
///
/// Usage:
///     qvfrompdbs <pdb1> <pdb2> ... <pdbN> > output.qv
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// PDB files to combine
    #[arg(required = true)]
    pdb_files: Vec<String>,
}

fn main() -> io::Result<()> {
    let args = Args::parse();

    let stdout = io::stdout();
    let mut handle = stdout.lock();

    for pdbfn in &args.pdb_files {
        let path = Path::new(pdbfn);
        let pdbtag = path
            .file_name()
            .and_then(|name| name.to_str())
            .map(|name| name.strip_suffix(".pdb").unwrap_or(name))
            .unwrap_or("UNKNOWN");

        writeln!(handle, "QV_TAG {}", pdbtag)?;

        let mut file = File::open(path)?;
        io::copy(&mut file, &mut handle)?;
    }

    Ok(())
}

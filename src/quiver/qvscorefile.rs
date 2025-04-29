use clap::Parser;
use std::collections::BTreeSet;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::path::Path;

/// Extracts the scorefile from a Quiver (.qv) file and writes it as a .sc file.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Quiver file to extract scores from
    qvfile: String,
}

fn main() {
    let args = Args::parse();

    if let Err(e) = extract_scorefile(&args.qvfile) {
        eprintln!("❌ Error: {}", e);
        std::process::exit(1);
    }
}

fn extract_scorefile(qvfile: &str) -> Result<(), String> {
    let file = File::open(qvfile).map_err(|e| format!("Failed to open file: {}", e))?;
    let reader = BufReader::new(file);

    let mut records: Vec<HashMap<String, String>> = Vec::new();
    let mut all_keys: BTreeSet<String> = BTreeSet::new();

    for line in reader.lines() {
        let line = line.map_err(|e| format!("Failed to read line: {}", e))?;
        if line.starts_with("QV_SCORE") {
            let splits: Vec<&str> = line.split_whitespace().collect();
            if splits.len() < 3 {
                continue;
            }
            let tag = splits[1];
            let mut scores = HashMap::new();
            let mut parse_error = false;

            for s in splits[2].split('|') {
                let mut kv = s.splitn(2, '=');
                let key = kv.next().unwrap_or("").to_string();
                let val = kv.next().unwrap_or("");
                if key.is_empty() || val.is_empty() {
                    parse_error = true;
                    break;
                }
                // Try to parse as float, but store as string for now
                if val.parse::<f64>().is_err() {
                    parse_error = true;
                    break;
                }
                scores.insert(key.clone(), val.to_string());
                all_keys.insert(key);
            }
            if parse_error {
                eprintln!("❌ Failed parsing scores for tag {}: Malformed score string", tag);
                continue;
            }
            scores.insert("tag".to_string(), tag.to_string());
            all_keys.insert("tag".to_string());
            records.push(scores);
        }
    }

    if records.is_empty() {
        return Err("No score lines found in Quiver file.".to_string());
    }

    // Output file name
    let outfn = Path::new(qvfile)
        .with_extension("sc")
        .to_string_lossy()
        .to_string();

    // Write as TSV
    let mut wtr = csv::WriterBuilder::new()
        .delimiter(b'\t')
        .has_headers(true)
        .from_path(&outfn)
        .map_err(|e| format!("Failed to create output file: {}", e))?;

    // Write header
    let header: Vec<&str> = all_keys.iter().map(|s| s.as_str()).collect();
    wtr.write_record(&header)
        .map_err(|e| format!("Failed to write header: {}", e))?;

    // Write records
    for rec in &records {
        let row: Vec<String> = all_keys
            .iter()
            .map(|k| rec.get(k).cloned().unwrap_or_else(|| "NaN".to_string()))
            .collect();
        wtr.write_record(&row)
            .map_err(|e| format!("Failed to write row: {}", e))?;
    }
    wtr.flush()
        .map_err(|e| format!("Failed to flush output: {}", e))?;

    println!("✅ Scorefile written to: {}", outfn);

    Ok(())
}

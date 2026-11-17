// Names/creates functions. args: <file>; lines "0x<addr> <name>". Skips names already applied.
//@category LongDark
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;
import java.nio.file.*;

public class NameFuncs extends GhidraScript {
    @Override
    public void run() throws Exception {
        int named = 0, created = 0, failed = 0;
        for (String line : Files.readAllLines(Paths.get(getScriptArgs()[0]))) {
            String[] t = line.trim().split(" ");
            if (t.length < 2) continue;
            Address a = toAddr(Long.decode(t[0]));
            Function f = getFunctionAt(a);
            if (f == null) {
                disassemble(a);
                f = createFunction(a, null);
                if (f != null) created++;
            }
            if (f == null) { failed++; continue; }
            try { f.setName(t[1], SourceType.USER_DEFINED); named++; }
            catch (Exception e) { failed++; }
        }
        println("NameFuncs: named " + named + " created " + created + " failed " + failed);
    }
}
